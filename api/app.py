"""
WarDashboard API: FastAPI app exposing losses (monthly) and economics (quarterly) as JSON.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from pipelines import EconomicsPipeline, LossesPipeline
from utils import dataframe_to_records

# Pipeline instances used by route handlers (patchable in tests)
_losses_pipeline = LossesPipeline()
_economics_pipeline = EconomicsPipeline()


def get_losses_grouped_monthly():
    """Fetch losses, parse, and group by month. Used by /losses and tests."""
    return _losses_pipeline.get_grouped_monthly()


def get_economics_grouped_quarterly():
    """Fetch economics and expand to quarterly. Used by /economics and tests."""
    return _economics_pipeline.get_grouped_quarterly()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Optional: cache data on startup if needed. For now we fetch on each request."""
    yield


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
    return JSONResponse(content=dataframe_to_records(df))


@app.get("/economics", response_class=JSONResponse)
def economics_grouped():
    """
    Returns economics data by quarter: year, period (first day of quarter, YYYY-MM-DD),
    gdp_growth, inflation, trade_pct_gdp, debt_pct_gdp. IMF WEO + World Bank, Russia; 2022–2025.
    """
    df = get_economics_grouped_quarterly()
    return JSONResponse(content=dataframe_to_records(df))


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
