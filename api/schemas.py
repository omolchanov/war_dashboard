"""Pydantic response models for API validation and OpenAPI docs."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class LossRecord(BaseModel):
    """Single quarterly losses record."""

    model_config = ConfigDict(extra="ignore")

    period: str
    year: int
    quarter: int
    personnel: int
    uav: int
    air_defense_systems: int


class EconomicsRecord(BaseModel):
    """Single quarterly economics record."""

    period: str
    year: int
    gdp_growth: float | None = None
    inflation: float | None = None
    trade_pct_gdp: float | None = None
    debt_pct_gdp: float | None = None
    balance_of_trade: float | None = None
    budget_balance_pct_gdp: float | None = None
    urals_oil_price: float | None = None

    model_config = ConfigDict(extra="ignore")


class RecruitingRecord(BaseModel):
    """Single quarterly recruiting record."""

    period: str
    year: int
    quarter: int
    contracts_signed_avg_per_quarter: float | None = None
    contracts_min_avg_per_quarter: float | None = None
    contracts_max_avg_per_quarter: float | None = None
    source: str | None = None

    model_config = ConfigDict(extra="ignore")


class PredictionResult(BaseModel):
    """Single prediction model result."""

    model: str
    predicted_end_quarter: str


class PredictionResponse(BaseModel):
    """Prediction endpoint response."""

    results: list[PredictionResult]


class RootEndpoints(BaseModel):
    """Root endpoint endpoints map."""

    losses: str
    economics: str
    recruiting: str
    prediction: str


class RootResponse(BaseModel):
    """Root endpoint response."""

    name: str
    endpoints: RootEndpoints | dict[str, Any]
