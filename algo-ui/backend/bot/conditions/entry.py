import numpy as np
import pandas as pd

def price_above_ema(df: pd.DataFrame, i: int) -> bool:
    # close > EMA30 at bar i
    return df["close"].iat[i] > df["EMA30"].iat[i]

def volume_spike(df: pd.DataFrame, i: int) -> bool:
    # volume > 2.910814 * rolling 40-bar average
    return df["volume"].iat[i] > 2.910814 * df["vol_avg_30"].iat[i]
