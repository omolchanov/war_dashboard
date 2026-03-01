"""Data helpers for prediction: extract time series from merged quarterly DataFrames."""

import pandas as pd


def get_personnel_series(df: pd.DataFrame) -> pd.Series:
    """Personnel losses as a time series (index = period)."""
    if "personnel" not in df.columns:
        raise ValueError("No 'personnel' column in merged data.")
    s = df.set_index("period")["personnel"].dropna()
    s.index = pd.PeriodIndex(s.index, freq="Q-DEC")
    return s.asfreq("Q-DEC").ffill().dropna()


def get_recruiting_series(df: pd.DataFrame) -> pd.Series | None:
    """Contracts signed (avg per quarter) as a time series, aligned to period. None if missing."""
    col = "contracts_signed_avg_per_quarter"
    if col not in df.columns:
        return None
    s = df.set_index("period")[col].dropna()
    if s.empty:
        return None
    s.index = pd.PeriodIndex(s.index, freq="Q-DEC")
    return s.asfreq("Q-DEC").ffill().dropna()
