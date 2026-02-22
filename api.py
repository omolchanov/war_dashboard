"""
WarDashboard API
FastAPI app exposing grouped losses (monthly) and economics (quarterly) as JSON.
"""

import math
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from economics_data_pipeline import (
    annual_to_quarterly,
    build_annual_economics,
    YEAR_MAX,
    YEAR_MIN,
)
from loses_data_pipeline import fetch_raw_data, parse_to_dataframe


def get_losses_grouped_monthly() -> pd.DataFrame:
    """Fetch losses, parse, and group by month (sum of personnel, uav, air_defense_systems). Keeps 2022–2025 only."""
    raw = fetch_raw_data()
    df = parse_to_dataframe(raw)
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    loss_cols = [c for c in df.columns if c not in ("date", "month")]
    grouped = df.groupby("month", as_index=False)[loss_cols].sum()
    # Restrict to YEAR_MIN–YEAR_MAX (2022–2025)
    grouped = grouped[
        (grouped["month"].dt.year >= YEAR_MIN)
        & (grouped["month"].dt.year <= YEAR_MAX)
    ].reset_index(drop=True)
    return grouped


def get_economics_grouped_quarterly() -> pd.DataFrame:
    """Fetch economics (IMF WEO + WB), 2022–2025, expand to quarterly (one row per quarter)."""
    df_annual = build_annual_economics()
    return annual_to_quarterly(df_annual)


def _nan_to_none(val):
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def _dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts with ISO dates and NaN -> null."""
    df = df.copy()
    for col in df.select_dtypes(include=["datetime64"]).columns:
        df[col] = df[col].dt.strftime("%Y-%m-%d")
    records = df.to_dict(orient="records")
    return [{k: _nan_to_none(v) for k, v in r.items()} for r in records]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Optional: cache data on startup if needed. For now we fetch on each request."""
    yield
    # shutdown


app = FastAPI(
    title="WarDashboard API",
    description="Grouped losses (monthly) and economics (quarterly) data.",
    lifespan=lifespan,
)


@app.get("/losses", response_class=JSONResponse)
def losses_grouped():
    """
    Returns losses data grouped by month: sum of personnel, uav, air_defense_systems per month.
    Historical 2022–2025 only (russian-casualties.in.ua).
    """
    df = get_losses_grouped_monthly()
    return JSONResponse(content=_dataframe_to_records(df))


@app.get("/economics", response_class=JSONResponse)
def economics_grouped():
    """
    Returns economics data by quarter: year, period (first day of quarter, YYYY-MM-DD, same format as losses month),
    gdp_growth, inflation, trade_pct_gdp, debt_pct_gdp. IMF WEO + World Bank, Russia; historical 2022–2025 only.
    """
    df = get_economics_grouped_quarterly()
    return JSONResponse(content=_dataframe_to_records(df))


@app.get("/")
def root():
    """API info and links to endpoints."""
    return {
        "name": "WarDashboard API",
        "endpoints": {
            "losses": "/losses  — monthly grouped losses (personnel, uav, air_defense_systems)",
            "economics": "/economics — quarterly grouped economics (gdp_growth, inflation, etc.)",
        },
    }
