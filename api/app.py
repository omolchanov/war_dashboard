"""
WarDashboard API: FastAPI app exposing losses (quarterly), economics (quarterly), recruiting (quarterly), and prediction results as JSON.
"""

import json
import subprocess
import sys
from pathlib import Path

from contextlib import asynccontextmanager

import requests
from fastapi import APIRouter, Depends, FastAPI, Query
from fastapi.responses import JSONResponse

from api.schemas import (
    EconomicsRecord,
    LossRecord,
    PredictionResponse,
    RecruitingRecord,
)
from pipelines import EconomicsPipeline, LossesPipeline, RecruitingPipeline
from utils import dataframe_to_records

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Pipeline instances used by route handlers (patchable in tests)
_losses_pipeline = LossesPipeline()
_economics_pipeline = EconomicsPipeline()
_recruiting_pipeline = RecruitingPipeline()


def get_losses_grouped_quarterly(refresh: bool = False):
    """Fetch losses, parse, and group by quarter. Used by /losses and tests."""
    return _losses_pipeline.get_grouped_quarterly()


def get_economics_grouped_quarterly(refresh: bool = False):
    """Fetch economics and expand to quarterly. Used by /economics and tests."""
    return _economics_pipeline.get_grouped_quarterly()


def get_recruiting(refresh: bool = False):
    """Recruiting by quarter (quarterly average from annual). Used by /recruiting."""
    return _recruiting_pipeline.get_recruiting_quarterly()


def get_prediction_results_data(refresh: bool = False):
    """Fetch prediction results by running the CLI subprocess (guarantees API/CLI consistency)."""
    proc = subprocess.run(
        [sys.executable, "-m", "prediction.run_prediction", "--json"],
        capture_output=True,
        text=True,
        cwd=_PROJECT_ROOT,
        timeout=120,
    )
    proc.check_returncode()
    data = json.loads(proc.stdout)
    return data["results"]


# Dependencies for injection (override in tests via app.dependency_overrides)
def get_losses_data(refresh: bool = Query(False, description="Ignored (no cache)")):
    """Dependency: returns losses DataFrame. Override in tests for mocked data."""
    return get_losses_grouped_quarterly()


def get_economics_data(refresh: bool = Query(False, description="Ignored (no cache)")):
    """Dependency: returns economics DataFrame. Override in tests for mocked data."""
    return get_economics_grouped_quarterly()


def get_recruiting_data(refresh: bool = Query(False, description="Ignored (no cache)")):
    """Dependency: returns recruiting DataFrame. Override in tests for mocked data."""
    return get_recruiting()


def get_prediction_data(refresh: bool = Query(False, description="Ignored (no cache)")):
    """Dependency: returns prediction results list. Override in tests for mocked data."""
    return get_prediction_results_data()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context (no cache)."""
    yield


app = FastAPI(
    title="WarDashboard API",
    description="Grouped losses (quarterly), economics (quarterly), and recruiting (quarterly) data.",
    lifespan=lifespan,
)


def _pipeline_error_handler(request, exc: Exception) -> JSONResponse:
    """Return 503 when pipelines fail (network, upstream errors)."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Data temporarily unavailable. Please try again later."},
    )


app.add_exception_handler(requests.RequestException, _pipeline_error_handler)
app.add_exception_handler(RuntimeError, _pipeline_error_handler)
app.add_exception_handler(ValueError, _pipeline_error_handler)
app.add_exception_handler(subprocess.CalledProcessError, _pipeline_error_handler)
app.add_exception_handler(subprocess.TimeoutExpired, _pipeline_error_handler)
app.add_exception_handler(json.JSONDecodeError, _pipeline_error_handler)


# v1 API router (versioned endpoints)
v1_router = APIRouter(prefix="/v1", tags=["v1"])


@v1_router.get("/losses", response_model=list[LossRecord])
def v1_losses_grouped(df=Depends(get_losses_data)):
    """Returns losses data grouped by quarter."""
    return dataframe_to_records(df)


@v1_router.get("/economics", response_model=list[EconomicsRecord])
def v1_economics_grouped(df=Depends(get_economics_data)):
    """Returns economics data by quarter."""
    return dataframe_to_records(df)


@v1_router.get("/recruiting", response_model=list[RecruitingRecord])
def v1_recruiting(df=Depends(get_recruiting_data)):
    """Returns recruiting by quarter."""
    return dataframe_to_records(df)


@v1_router.get("/prediction", response_model=PredictionResponse)
def v1_prediction(results=Depends(get_prediction_data)):
    """Returns prediction results."""
    return {"results": results}


@v1_router.get("/")
def v1_root():
    """v1 API info."""
    return {
        "version": "1",
        "endpoints": {
            "losses": "/v1/losses",
            "economics": "/v1/economics",
            "recruiting": "/v1/recruiting",
            "prediction": "/v1/prediction",
        },
    }


app.include_router(v1_router)


@app.get("/losses", response_class=JSONResponse)
def losses_grouped(df=Depends(get_losses_data)):
    """
    Returns losses data grouped by quarter: period (first day of quarter), year, quarter,
    sum of personnel, uav, air_defense_systems per quarter. Historical 2022–2025 only (russian-casualties.in.ua).
    """
    return JSONResponse(content=dataframe_to_records(df))


@app.get("/economics", response_class=JSONResponse)
def economics_grouped(df=Depends(get_economics_data)):
    """
    Returns economics data by quarter: year, period (first day of quarter, YYYY-MM-DD),
    gdp_growth, inflation, trade_pct_gdp, debt_pct_gdp, balance_of_trade (current US$),
    budget_balance_pct_gdp (surplus/deficit % GDP; negative = deficit), urals_oil_price (quarterly avg, $/bbl).
    IMF WEO + World Bank + IMF PCPS (oil), Russia; 2022–2025.
    """
    return JSONResponse(content=dataframe_to_records(df))


@app.get("/recruiting", response_class=JSONResponse)
def recruiting(df=Depends(get_recruiting_data)):
    """
    Returns Russia army recruiting by quarter: quarterly average (annual total ÷ 4).
    period (first day of quarter), year, quarter, contracts_signed_avg_per_quarter,
    contracts_min_avg_per_quarter, contracts_max_avg_per_quarter, source. Curated data.
    """
    return JSONResponse(content=dataframe_to_records(df))


@app.get("/prediction", response_class=JSONResponse)
def prediction(results=Depends(get_prediction_data)):
    """
    Returns prediction results: list of { model, predicted_end_quarter } for each model
    (Exponential smoothing, SARIMAX, Ridge recursive). Uses losses and recruiting data.
    """
    return JSONResponse(content={"results": results})


@app.get("/")
def root():
    """API info and links to endpoints."""
    return {
        "name": "WarDashboard API",
        "endpoints": {
            "losses": "/losses  — quarterly grouped losses (period, year, quarter, personnel, uav, air_defense_systems)",
            "economics": "/economics — quarterly grouped economics (gdp_growth, inflation, balance_of_trade, budget_balance_pct_gdp, urals_oil_price, etc.)",
            "recruiting": "/recruiting — quarterly recruiting (quarterly average from curated annual data)",
            "prediction": "/prediction — prediction results (model, predicted_end_quarter) for Expo, SARIMAX, Ridge",
            "v1": "/v1 — versioned API (same endpoints under /v1/)",
        },
    }
