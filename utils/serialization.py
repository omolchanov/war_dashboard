"""
Serialize DataFrames to JSON-friendly records (ISO dates, NaN → null).
"""

import math

import pandas as pd


def _nan_to_none(val):
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts with ISO dates and NaN → null."""
    df = df.copy()
    for col in df.select_dtypes(include=["datetime64"]).columns:
        df[col] = df[col].dt.strftime("%Y-%m-%d")
    records = df.to_dict(orient="records")
    return [{k: _nan_to_none(v) for k, v in r.items()} for r in records]
