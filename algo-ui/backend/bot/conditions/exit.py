import numpy as np
import pandas as pd

def target_hit(df: pd.DataFrame, i: int, ep: float):
    # high >= 1.212378 * entry
    if df["high"].iat[i] >= ep * 1.212378:
        return (True, "Target hit")
    return (False, None)

def stoploss_hit(df: pd.DataFrame, i: int, ep: float):
    # low <= 0.612951 * entry
    if df["low"].iat[i] <= ep * 0.612951:
        return (True, "Stoploss hit")
    return (False, None)

def close_below_ema(df: pd.DataFrame, i: int, ep: float):
    # close < EMA30
    if df["close"].iat[i] < df["EMA30"].iat[i]:
        return (True, "Closed<EMA")
    return (False, None)

def doji_and_6pct_profit(df: pd.DataFrame, i: int, ep: float):
    # small body + >=6% profit
    o = df["open"].iat[i]
    c = df["close"].iat[i]
    if not (np.isfinite(o) and np.isfinite(c) and np.isfinite(ep) and ep > 0):
        return (False, None)
    body_pct = abs(c - o) / o if o else 1e9
    ret = (c - ep) / ep
    if body_pct < 0.0015 and ret > 0.06:
        return (True, "Doji+6%")
    return (False, None)
