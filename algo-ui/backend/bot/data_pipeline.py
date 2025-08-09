import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

from growwapi import GrowwAPI

from .clock import INDIAN_TZ
from .clock import now_india
from .session import API_AUTH_TOKEN

# Project-relative paths
BASE_DIR = Path(__file__).resolve().parents[2]
TICKER_CSV: str = str(BASE_DIR / "data" / "Ticker.csv")
SELECTION_JSON: str = str(BASE_DIR / "data" / "selected_tickers.json")
DATA_DIR: str   = str(BASE_DIR / "backend" / "data_cache")

# Historical chunk limits (days) per interval (unchanged)
INTERVAL_LIMITS: Dict[int, Optional[int]] = {
    1: 7, 5: 15, 10: 30, 60: 150, 240: 365, 1440: 1080, 10080: None
}

os.makedirs(DATA_DIR, exist_ok=True)
groww = GrowwAPI(API_AUTH_TOKEN)

def _ensure_dtindex_ist(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]
    if df.empty:
        return df
    if df.index.tz is None:
        df.index = df.index.tz_localize(INDIAN_TZ)
    else:
        df.index = df.index.tz_convert(INDIAN_TZ)
    return df.sort_index()

def load_cache(symbol: str) -> Optional[pd.DataFrame]:
    path = os.path.join(DATA_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return _ensure_dtindex_ist(df)
    except Exception:
        return None

def save_cache(df: pd.DataFrame, symbol: str) -> None:
    if df is None or df.empty:
        return
    path = os.path.join(DATA_DIR, f"{symbol}.csv")
    to_save = _ensure_dtindex_ist(df.copy())
    if isinstance(to_save.index, pd.DatetimeIndex) and to_save.index.tz is not None:
        to_save.index = to_save.index.tz_localize(None)
    try:
        to_save.to_csv(path)
    except Exception:
        pass

def fetch_historical_data(
    groww_client: GrowwAPI,
    symbol: str,
    interval: int,
    start_dt: datetime,
    end_dt: datetime
) -> pd.DataFrame:
    max_days = INTERVAL_LIMITS.get(interval, 7)
    raw_candles: List[list] = []
    cur = start_dt
    while cur < end_dt:
        nxt = min(cur + timedelta(days=max_days), end_dt) if max_days else end_dt
        s1 = cur.strftime("%Y-%m-%d %H:%M:%S")
        s2 = nxt.strftime("%Y-%m-%d %H:%M:%S")
        try:
            resp = groww_client.get_historical_candle_data(
                trading_symbol=symbol,
                exchange=GrowwAPI.EXCHANGE_NSE,
                segment=GrowwAPI.SEGMENT_CASH,
                start_time=s1,
                end_time=s2,
                interval_in_minutes=interval,
            )
            raw_candles.extend(resp.get("candles", []))
        except Exception:
            break
        cur = nxt + timedelta(minutes=interval)
    if not raw_candles:
        return pd.DataFrame()
    df = pd.DataFrame(raw_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert(INDIAN_TZ)
    return df.set_index("datetime").drop(columns=["timestamp"]).sort_index()

def convert_to_15min(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = _ensure_dtindex_ist(df)
    if df.empty:
        return df
    return (
        df.resample("15min")
          .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
          .dropna()
    )

def _get_effective_end(test_mode: bool = False) -> datetime:
    # same behavior as before: test_mode returns "now"
    from .clock import WEEKEND_DAYS, MARKET_CLOSE_TIME, INDIAN_TZ
    cur = now_india()
    if test_mode:
        return cur
    if cur.weekday() in WEEKEND_DAYS or cur.time() >= MARKET_CLOSE_TIME:
        from datetime import datetime as _dt
        close_dt = _dt.combine(cur.date(), MARKET_CLOSE_TIME)
        return INDIAN_TZ.localize(close_dt)
    return cur

def update_data(symbol: str, *, test_mode: bool = False) -> pd.DataFrame:
    df = load_cache(symbol)
    if df is not None and not df.empty:
        start = df.index[-1] + relativedelta(minutes=1)
    else:
        start = now_india() - relativedelta(months=3)
    end_dt = _get_effective_end(test_mode=test_mode)
    if start >= end_dt:
        return df if df is not None else pd.DataFrame()
    raw = fetch_historical_data(groww, symbol, 5, start, end_dt)
    df15 = convert_to_15min(raw)
    if df is not None and not df.empty:
        combined = pd.concat([df, df15]).sort_index()
        combined = combined[~combined.index.duplicated(keep="last")]
        df = combined
    else:
        df = df15
    save_cache(df, symbol)
    return df
