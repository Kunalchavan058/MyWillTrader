# -*- coding: utf-8 -*-
"""
Async NSE bot (modularized).
- Same strategy, sizing, and flow as before.
- 'test_mode' toggle, UI callbacks (progress_cb, state_cb).
- Conditions live in backend/bot/conditions/*.py (unchanged).
- New modules: session (API), clock (time utils), data_pipeline (data/cache),
  strategy (strategy wrapper), orders (qty + order).
"""

import os
import random
import asyncio
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Callable, Any
from pathlib import Path
import json

import numpy as np
import pandas as pd

from growwapi import GrowwAPI

# --- modular imports (moved code, logic unchanged) ---
from .session import API_AUTH_TOKEN
from .clock import (
    now_india,
    is_market_open,
    seconds_until_market_open,
    seconds_to_next_bar,
)
from .data_pipeline import (
    update_data,              # update_data(symbol, *, test_mode=False) -> pd.DataFrame
    TICKER_CSV,               # data\Ticker.csv (project-root relative)
    SELECTION_JSON,           # data\selected_tickers.json
)
from .strategy import ModularStrategy
from .orders import compute_qty, place_market_order
from .conditions import (
    price_above_ema,
    volume_spike,
    target_hit,
    stoploss_hit,
    close_below_ema,
    doji_and_6pct_profit,
)

# =========================
# ====== CONFIG AREA ======
# =========================

# Project paths are computed where needed in submodules.
# Keep user-tunable params here (unchanged values).
CAPITAL_PER_TRADE: float = 100.0
POLL_INTERVAL_MIN: int = 15
ORDER_PRODUCT: str  = GrowwAPI.PRODUCT_MIS
ORDER_VALIDITY: str = GrowwAPI.VALIDITY_DAY

# Logging
LOG_LEVEL = logging.INFO

# Concurrency
MAX_WORKERS: int       = 8
CONCURRENCY_LIMIT: int = 5

# =========================
# ====== RUNTIME SETUP ====
# =========================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=LOG_LEVEL,
    datefmt="%-Y-%m-%d %H:%M:%S" if os.name != "nt" else "%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

try:
    EXECUTOR  # type: ignore
except NameError:
    EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Async wrappers for blocking calls
async def update_data_async(symbol: str, *, test_mode: bool) -> pd.DataFrame:
    loop = asyncio.get_running_loop()
    # keyword-only param preserved
    return await loop.run_in_executor(EXECUTOR, lambda: update_data(symbol, test_mode=test_mode))

async def place_market_order_async(sym: str, side: str, qty: int,
                                   product: Optional[str] = None,
                                   validity: Optional[str] = None) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(EXECUTOR, place_market_order, sym, side, qty, product, validity)

# =========================
# ====== BOT RUNTIME  =====
# =========================

@dataclass
class PositionState:
    in_trade: bool = False
    entry_price: Optional[float] = None
    qty: int = 0

def render_status(tickers: List[str], states: Dict[str, PositionState], last_prices: Dict[str, float]) -> str:
    lines = ["----- BAR SUMMARY -----",
             f"{'TICKER':<12}{'STATE':<6}{'QTY':<6}{'ENTRY':<10}{'LAST':<10}{'P&L%':<8}"]
    for t in tickers:
        st = states[t]; last = last_prices.get(t)
        state_str = "IN" if st.in_trade else "OUT"
        qty = st.qty if st.in_trade else 0
        entry = f"{st.entry_price:.2f}" if st.entry_price else "-"
        last_s = f"{last:.2f}" if last is not None else "-"
        pnl_s = "-"
        if st.in_trade and last is not None and st.entry_price:
            pnl_pct = 100.0 * (last - st.entry_price) / st.entry_price
            pnl_s = f"{pnl_pct:+.2f}"
        lines.append(f"{t:<12}{state_str:<6}{qty:<6}{entry:<10}{last_s:<10}{pnl_s:<8}")
    msg = "\n".join(lines)
    logger.info(msg)
    return msg

def _load_symbols_from_csv() -> List[str]:
    if not os.path.exists(TICKER_CSV):
        raise FileNotFoundError(f"{TICKER_CSV} not found. Expect a CSV with a 'SYMBOL' column.")
    df_csv = pd.read_csv(TICKER_CSV)
    if "SYMBOL" not in df_csv.columns:
        raise ValueError("Ticker.csv must contain a 'SYMBOL' column.")
    symbols = [s for s in df_csv["SYMBOL"].dropna().astype(str).tolist() if s.strip()]
    if not symbols:
        raise ValueError("No symbols found in Ticker.csv")
    return symbols

def _load_selected_symbols(default_symbols: List[str]) -> List[str]:
    if not os.path.exists(SELECTION_JSON):
        return default_symbols
    try:
        data = json.loads(Path(SELECTION_JSON).read_text(encoding="utf-8"))
        sel = [s for s in data.get("symbols", []) if s]
        return sel if sel else default_symbols
    except Exception:
        return default_symbols

# Callback types
ProgressCB = Optional[Callable[[str], None]]
StateCB    = Optional[Callable[[Dict[str, Any]], None]]

async def warm_up_one(ticker: str, gate: asyncio.Semaphore, *, test_mode: bool, progress_cb: ProgressCB) -> None:
    async with gate:
        if progress_cb: progress_cb(f"[{ticker}] warm-up fetch…")
        await update_data_async(ticker, test_mode=test_mode)

async def process_ticker(
    ticker: str,
    state: PositionState,
    capital_per_trade: float,
    concurrency_gate: asyncio.Semaphore,
    progress_cb: ProgressCB = None,
    *,
    test_mode: bool
) -> Dict[str, Optional[float]]:
    await asyncio.sleep(random.uniform(0.05, 0.25))  # jitter

    async with concurrency_gate:
        if progress_cb: progress_cb(f"[{ticker}] fetching/merging data…")
        df15 = await update_data_async(ticker, test_mode=test_mode)

    result = {"ticker": ticker, "last_close": None}

    if df15 is None or df15.empty:
        msg = f"{ticker}: no data, skipping."
        logger.info(msg)
        if progress_cb: progress_cb(msg)
        return result

    strat = ModularStrategy(df15)
    strat.prepare_indicators()

    # Entry rules (same order)
    strat.add_entry_condition(price_above_ema)
    strat.add_entry_condition(volume_spike)

    # Exit rules (same order)
    strat.add_exit_condition(target_hit)
    strat.add_exit_condition(stoploss_hit)
    strat.add_exit_condition(close_below_ema)
    strat.add_exit_condition(doji_and_6pct_profit)

    i = len(df15) - 1
    if i < 0:
        return result

    last_close = float(df15["close"].iat[i])
    result["last_close"] = last_close

    # ENTRY
    if not state.in_trade and strat.should_enter(i):
        ep = float(df15["open"].iat[i])
        qty = compute_qty(capital_per_trade, ep)
        if qty <= 0:
            msg = f"{ticker}: qty=0 for capital={capital_per_trade}, price={ep:.2f}"
            logger.info(msg)
            if progress_cb: progress_cb(msg)
            return result

        async with concurrency_gate:
            await place_market_order_async(ticker, GrowwAPI.TRANSACTION_TYPE_BUY, qty)

        state.in_trade = True
        state.entry_price = ep
        state.qty = qty
        msg = f"ENTERED {ticker} @ {ep:.2f} (qty={qty})"
        logger.info(msg)
        if progress_cb: progress_cb(msg)
        return result  # do not also exit on the same bar

    # EXIT
    if state.in_trade:
        flag, reason = strat.should_exit(i, state.entry_price)
        if flag:
            xp = float(df15["close"].iat[i])
            qty = max(state.qty, 0)

            if qty > 0:
                async with concurrency_gate:
                    await place_market_order_async(ticker, GrowwAPI.TRANSACTION_TYPE_SELL, qty)
                msg = f"EXITED {ticker} @ {xp:.2f} (qty={qty}, reason={reason})"
                logger.info(msg)
                if progress_cb: progress_cb(msg)
            else:
                warn = f"{ticker}: no stored qty to exit."
                logger.warning(warn)
                if progress_cb: progress_cb(warn)

            state.in_trade = False
            state.entry_price = None
            state.qty = 0

    return result

async def run_bot(progress_cb: ProgressCB = None, state_cb: StateCB = None, *, test_mode: bool = False) -> None:
    symbols = _load_symbols_from_csv()
    tickers = _load_selected_symbols(symbols)
    logger.info(f"Universe: {tickers} | test_mode={test_mode}")
    if progress_cb: progress_cb(f"Universe: {', '.join(tickers)} | test_mode={test_mode}")

    # State per ticker
    states: Dict[str, PositionState] = {t: PositionState() for t in tickers}

    # Bounded concurrency gate
    gate = asyncio.Semaphore(CONCURRENCY_LIMIT)

    # Warm up cache concurrently
    if progress_cb: progress_cb("Warming up caches…")
    await asyncio.gather(*(warm_up_one(t, gate, test_mode=test_mode, progress_cb=progress_cb) for t in tickers))
    if progress_cb: progress_cb("Warm‑up done. Starting async live loop…")

    while True:
        now_ts = now_india()

        if not is_market_open(now_ts) and not test_mode:
            secs = seconds_until_market_open(now_ts)
            msg = f"Market closed, next open in {int(secs)}s"
            logger.warning(msg)
            if progress_cb: progress_cb(msg)
            await asyncio.sleep(min(secs, 600))
            continue

        sleep_s = seconds_to_next_bar(now_ts, POLL_INTERVAL_MIN)
        tick = f"⏱️ Time to next {POLL_INTERVAL_MIN}-min candle: {int(sleep_s)}s"
        logger.info(tick)
        if progress_cb: progress_cb(tick)
        await asyncio.sleep(sleep_s)

        if progress_cb: progress_cb(f"📊 Processing {len(tickers)} tickers concurrently…")
        tasks = [
            process_ticker(
                ticker=t,
                state=states[t],
                capital_per_trade=CAPITAL_PER_TRADE,
                concurrency_gate=gate,
                progress_cb=progress_cb,
                test_mode=test_mode
            )
            for t in tickers
        ]
        results = await asyncio.gather(*tasks)
        last_prices = {r["ticker"]: r["last_close"] for r in results if r and r.get("last_close") is not None}
        summary = render_status(tickers, states, last_prices)
        if progress_cb: progress_cb(summary)

        # ---- send structured state snapshot to UI ----
        if state_cb:
            rows = []
            for t in tickers:
                st = states[t]
                last = last_prices.get(t)
                pnl_pct = None
                if st.in_trade and last is not None and st.entry_price:
                    pnl_pct = 100.0 * (last - st.entry_price) / st.entry_price
                rows.append({
                    "ticker": t,
                    "state": "IN" if st.in_trade else "OUT",
                    "qty": st.qty if st.in_trade else 0,
                    "entry": st.entry_price,
                    "last": last,
                    "pnl_pct": pnl_pct,
                })
            snapshot = {"type": "state", "ts": now_india().isoformat(), "rows": rows}
            try:
                state_cb(snapshot)
            except Exception:
                pass

# =========================
# ======= RUNNERS =========
# =========================

bot_task: Optional[asyncio.Task] = None

def _running_loop():
    try:
        loop = asyncio.get_running_loop()
        return loop if loop.is_running() else None
    except RuntimeError:
        return None

async def start_bot_background(progress_cb: ProgressCB = None, state_cb: StateCB = None, *, test_mode: bool = False):
    global bot_task
    loop = _running_loop()
    if not loop:
        await run_bot(progress_cb=progress_cb, state_cb=state_cb, test_mode=test_mode)
        return
    try:
        import nest_asyncio  # type: ignore
        nest_asyncio.apply()
    except Exception:
        pass
    if bot_task and not bot_task.done():
        print("Bot is already running.")
        return bot_task
    bot_task = loop.create_task(run_bot(progress_cb=progress_cb, state_cb=state_cb, test_mode=test_mode))
    print("Bot started as background task. To stop: await stop_bot()")
    return bot_task

async def stop_bot():
    global bot_task
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        bot_task = None
    print("Bot stopped.")
