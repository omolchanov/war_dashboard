"""
WarDashboard API: FastAPI app exposing losses (quarterly), economics (quarterly), and recruiting (quarterly) as JSON.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from pipelines import EconomicsPipeline, LossesPipeline, RecruitingPipeline
from utils import dataframe_to_records

# Pipeline instances used by route handlers (patchable in tests)
_losses_pipeline = LossesPipeline()
_economics_pipeline = EconomicsPipeline()
_recruiting_pipeline = RecruitingPipeline()


def get_losses_grouped_quarterly():
    """Fetch losses, parse, and group by quarter. Used by /losses and tests."""
    return _losses_pipeline.get_grouped_quarterly()


def get_economics_grouped_quarterly():
    """Fetch economics and expand to quarterly. Used by /economics and tests."""
    return _economics_pipeline.get_grouped_quarterly()


def get_recruiting():
    """Recruiting by quarter (quarterly average from annual). Used by /recruiting."""
    return _recruiting_pipeline.get_recruiting_quarterly()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Optional: cache data on startup if needed. For now we fetch on each request."""
    yield


app = FastAPI(
    title="WarDashboard API",
    description="Grouped losses (quarterly), economics (quarterly), and recruiting (quarterly) data.",
    lifespan=lifespan,
)


@app.get("/losses", response_class=JSONResponse)
def losses_grouped():
    """
    Returns losses data grouped by quarter: period (first day of quarter), year, quarter,
    sum of personnel, uav, air_defense_systems per quarter. Historical 2022–2025 only (russian-casualties.in.ua).
    """
    df = get_losses_grouped_quarterly()
    return JSONResponse(content=dataframe_to_records(df))


@app.get("/economics", response_class=JSONResponse)
def economics_grouped():
    """
    Returns economics data by quarter: year, period (first day of quarter, YYYY-MM-DD),
    gdp_growth, inflation, trade_pct_gdp, debt_pct_gdp, balance_of_trade (current US$),
    budget_balance_pct_gdp (surplus/deficit % GDP; negative = deficit), urals_oil_price (quarterly avg, $/bbl).
    IMF WEO + World Bank + IMF PCPS (oil), Russia; 2022–2025.
    """
    df = get_economics_grouped_quarterly()
    return JSONResponse(content=dataframe_to_records(df))


@app.get("/recruiting", response_class=JSONResponse)
def recruiting():
    """
    Returns Russia army recruiting by quarter: quarterly average (annual total ÷ 4).
    period (first day of quarter), year, quarter, contracts_signed_avg_per_quarter,
    contracts_min_avg_per_quarter, contracts_max_avg_per_quarter, source. Curated data.
    """
    df = get_recruiting()
    return JSONResponse(content=dataframe_to_records(df))


@app.get("/")
def root():
    """API info and links to endpoints."""
    return {
        "name": "WarDashboard API",
        "endpoints": {
            "losses": "/losses  — quarterly grouped losses (period, year, quarter, personnel, uav, air_defense_systems)",
            "economics": "/economics — quarterly grouped economics (gdp_growth, inflation, balance_of_trade, budget_balance_pct_gdp, urals_oil_price, etc.)",
            "recruiting": "/recruiting — quarterly recruiting (quarterly average from curated annual data)",
        },
    }
