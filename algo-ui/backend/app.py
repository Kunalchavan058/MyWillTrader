from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
import json
import asyncio
from typing import Set

from . import bot as trading_bot

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"
CSV_PATH = DATA_DIR / "Ticker.csv"
SELECTION_JSON = DATA_DIR / "selected_tickers.json"
SELECTION_TXT = DATA_DIR / "selected_tickers.txt"
SETTINGS_JSON = DATA_DIR / "settings.json"

app = FastAPI(title="Ticker Selector + Bot Controller")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_index():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(index))

# --------- CSV + selection ---------

@app.get("/api/tickers")
def list_tickers():
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="Ticker.csv not found in /data")
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {e}")
    if "SYMBOL" not in df.columns:
        raise HTTPException(status_code=400, detail="CSV must include a 'SYMBOL' column")
    symbols = [str(s).strip() for s in df["SYMBOL"].dropna().tolist() if str(s).strip()]
    return {"symbols": symbols}

class SelectionPayload(BaseModel):
    symbols: list[str]

@app.post("/api/selection")
def save_selection(payload: SelectionPayload):
    unique, seen = [], set()
    for s in payload.symbols:
        s2 = s.strip()
        if s2 and s2 not in seen:
            seen.add(s2); unique.append(s2)
    SELECTION_JSON.write_text(json.dumps({"symbols": unique}, indent=2), encoding="utf-8")
    SELECTION_TXT.write_text("\n".join(unique) + ("\n" if unique else ""), encoding="utf-8")
    return {"saved": len(unique), "symbols": unique, "paths": {"json": str(SELECTION_JSON), "txt": str(SELECTION_TXT)}}

@app.get("/api/selection")
def get_selection():
    if not SELECTION_JSON.exists():
        return {"symbols": []}
    try:
        data = json.loads(SELECTION_JSON.read_text(encoding="utf-8"))
        return {"symbols": data.get("symbols", [])}
    except Exception:
        return {"symbols": []}

# --------- Settings (Test Mode) ---------

class SettingsPayload(BaseModel):
    test_mode: bool

def _load_settings():
    if not SETTINGS_JSON.exists():
        return {"test_mode": False}
    try:
        data = json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
        return {"test_mode": bool(data.get("test_mode", False))}
    except Exception:
        return {"test_mode": False}

@app.get("/api/settings")
def get_settings():
    return _load_settings()

@app.post("/api/settings")
def save_settings(payload: SettingsPayload):
    settings = {"test_mode": bool(payload.test_mode)}
    SETTINGS_JSON.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings

# --------- Bot control + WebSocket (logs + state) ---------

BOT_TASK: asyncio.Task | None = None
CLIENTS: Set[WebSocket] = set()
OUT_QUEUE: asyncio.Queue[str] = asyncio.Queue()

def _emit_text(msg: str) -> None:
    try:
        OUT_QUEUE.put_nowait(msg)
    except Exception:
        pass

def _emit_state(snapshot: dict) -> None:
    try:
        OUT_QUEUE.put_nowait(json.dumps(snapshot))
    except Exception:
        pass

async def _broadcaster():
    while True:
        msg = await OUT_QUEUE.get()
        dead = []
        for ws in list(CLIENTS):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for d in dead:
            CLIENTS.discard(d)

@app.on_event("startup")
async def on_startup():
    app.state.broadcast_task = asyncio.create_task(_broadcaster())

@app.on_event("shutdown")
async def on_shutdown():
    global BOT_TASK
    if BOT_TASK and not BOT_TASK.done():
        BOT_TASK.cancel()
        try:
            await BOT_TASK
        except asyncio.CancelledError:
            pass
    bt = getattr(app.state, "broadcast_task", None)
    if bt:
        bt.cancel()
        try:
            await bt
        except asyncio.CancelledError:
            pass

@app.websocket("/ws")
async def ws_logs(ws: WebSocket):
    await ws.accept()
    CLIENTS.add(ws)
    try:
        await ws.send_text("Connected to bot stream.")
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        pass
    finally:
        CLIENTS.discard(ws)

@app.post("/api/bot/start")
async def bot_start():
    global BOT_TASK
    if BOT_TASK and not BOT_TASK.done():
        return {"status": "already_running"}
    if trading_bot.API_AUTH_TOKEN == "REPLACE_WITH_YOUR_TOKEN":
        raise HTTPException(status_code=400, detail="Set API_AUTH_TOKEN in backend/bot.py first.")
    settings = _load_settings()
    test_mode = bool(settings.get("test_mode", False))
    _emit_text(f"Starting bot with test_mode={test_mode} …")
    BOT_TASK = asyncio.create_task(trading_bot.run_bot(progress_cb=_emit_text, state_cb=_emit_state, test_mode=test_mode))
    return {"status": "starting", "test_mode": test_mode}

@app.post("/api/bot/stop")
async def bot_stop():
    global BOT_TASK
    if not BOT_TASK or BOT_TASK.done():
        return {"status": "not_running"}
    BOT_TASK.cancel()
    try:
        await BOT_TASK
    except asyncio.CancelledError:
        pass
    BOT_TASK = None
    _emit_text("Bot stopped.")
    return {"status": "stopped"}

@app.get("/api/bot/status")
def bot_status():
    running = BOT_TASK is not None and not BOT_TASK.done()
    settings = _load_settings()
    return {"running": running, "test_mode": bool(settings.get("test_mode", False))}
