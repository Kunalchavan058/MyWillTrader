import numpy as np
import pandas as pd

class ModularStrategy:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.entry_conditions = []
        self.exit_conditions = []

    def prepare_indicators(self) -> None:
        if self.df is None or self.df.empty:
            return
        # label kept as-is (EMA30 with span=40)
        self.df["EMA30"] = self.df["close"].ewm(span=40, adjust=False).mean()
        self.df["vol_avg_30"] = self.df["volume"].rolling(40, min_periods=40).mean()

    def add_entry_condition(self, fn) -> None:
        self.entry_conditions.append(fn)

    def add_exit_condition(self, fn) -> None:
        self.exit_conditions.append(fn)

    def ready_for_signals(self, i: int) -> bool:
        if i < 1 or len(self.df) < 41:
            return False
        ema_ok = np.isfinite(self.df["EMA30"].iat[i])
        vol_ok = np.isfinite(self.df["vol_avg_30"].iat[i])
        return bool(ema_ok and vol_ok)

    def should_enter(self, i: int) -> bool:
        if not self.ready_for_signals(i):
            return False
        return all(cond(self.df, i - 1) for cond in self.entry_conditions)

    def should_exit(self, i: int, ep: float):
        if i < 0 or ep is None or not np.isfinite(ep):
            return (False, None)
        for cond in self.exit_conditions:
            flag, reason = cond(self.df, i, ep)
            if flag:
                return (True, reason)
        return (False, None)
