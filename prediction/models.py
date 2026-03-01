"""
Prediction models: pure logic for war-end quarter prediction.
No printing. Used by API and CLI.
"""

import random

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sktime.forecasting.compose import make_reduction
from sktime.forecasting.exp_smoothing import ExponentialSmoothing
from sktime.forecasting.sarimax import SARIMAX

from prediction.data import get_personnel_series, get_recruiting_series
from utils import load_quarterly_merged


def predict_end_quarter(
    y: pd.Series,
    forecaster,
    fh_quarters: int,
    threshold: float,
    X: pd.DataFrame | None = None,
    X_future: pd.DataFrame | None = None,
) -> tuple[pd.Series | None, object]:
    """Fit forecaster, predict fh_quarters ahead. Optional X (exog) and X_future for predict."""
    fh = list(range(1, fh_quarters + 1))
    try:
        if X is not None and X_future is not None and not X.empty and not X_future.empty:
            forecaster.fit(y, X=X)
            pred = forecaster.predict(fh=fh, X=X_future)
        else:
            forecaster.fit(y)
            pred = forecaster.predict(fh=fh)
        return (pred, forecaster)
    except Exception:
        return (None, None)


def first_quarter_below(pred: pd.Series, threshold: float):
    """First period index where pred < threshold, or None."""
    if pred is None or pred.empty:
        return None
    below = pred < threshold
    if below.any():
        return pred.index[below][0]
    return None


def _align_y_X(y: pd.Series, recruiting: pd.Series | None) -> tuple[pd.Series, pd.DataFrame | None]:
    """Align y and recruiting on common index; return (y_aligned, X_aligned as DataFrame or None)."""
    if recruiting is None or recruiting.empty:
        return (y, None)
    common = y.index.intersection(recruiting.index)
    y_a = y.loc[common].dropna()
    x_a = recruiting.reindex(common).ffill().bfill()
    x_a = x_a.loc[y_a.index].dropna()
    y_a = y_a.loc[x_a.index]
    if y_a.empty or x_a.empty:
        return (y, None)
    X = x_a.to_frame("recruiting")
    return (y_a, X)


def get_prediction_results(verbose: bool = False, include_details: bool = False) -> list[dict] | tuple[list[dict], dict]:
    """
    Run all prediction models (Exponential smoothing, SARIMAX, Ridge recursive).
    Returns list of dicts with keys: model (str), predicted_end_quarter (str).
    No printing. Uses losses and recruiting data from pipelines.
    When include_details=True, returns (results, details) for CLI display.
    """
    random.seed(42)
    np.random.seed(42)
    merged = load_quarterly_merged(verbose=verbose)
    y = get_personnel_series(merged)
    recruiting = get_recruiting_series(merged)
    if len(y) < 4:
        return []

    recent_mean = float(y.rolling(min(8, len(y))).mean().dropna().iloc[-1])
    threshold = recent_mean * 0.05
    fh_quarters = 20
    fh = list(range(1, fh_quarters + 1))

    recruiting_forecast = None
    X_future = None
    if recruiting is not None and len(recruiting) >= 4:
        try:
            expo_rec = ExponentialSmoothing(trend="add", seasonal="add", sp=4, random_state=42)
            expo_rec.fit(recruiting)
            recruiting_forecast = expo_rec.predict(fh=fh)
            X_future = recruiting_forecast.to_frame("recruiting")
        except Exception:
            pass

    y_fit, X_fit = _align_y_X(y, recruiting)
    results = []
    pred_sar = None
    pred_ridge = None

    # 1. Exponential smoothing
    expo = ExponentialSmoothing(trend="add", seasonal="add", sp=4, random_state=42)
    pred_expo, fitted_expo = predict_end_quarter(y, expo, fh_quarters, threshold)
    end_expo = first_quarter_below(pred_expo, threshold) if pred_expo is not None else None
    results.append(
        {
            "model": "Exponential smoothing",
            "predicted_end_quarter": str(end_expo) if end_expo is not None else "— (not below threshold in 20q)",
        }
    )

    # 2. SARIMAX
    if X_fit is not None and X_future is not None and len(X_fit) >= 6:
        try:
            sarimax = SARIMAX(order=(1, 0, 0), seasonal_order=(0, 0, 0, 4), trend="c", random_state=42)
            pred_sar, _ = predict_end_quarter(y_fit, sarimax, fh_quarters, threshold, X=X_fit, X_future=X_future)
            end_sar = first_quarter_below(pred_sar, threshold) if pred_sar is not None else None
            results.append(
                {
                    "model": "SARIMAX (losses + recruiting)",
                    "predicted_end_quarter": str(end_sar) if end_sar is not None else "— (not below threshold in 20q)",
                }
            )
        except Exception:
            results.append({"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (fit/predict failed)"})
    else:
        results.append({"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (no recruiting or too short)"})

    # 3. Ridge recursive
    if X_fit is not None and X_future is not None and len(y_fit) >= 6:
        try:
            ridge_rec = make_reduction(Ridge(alpha=1.0, random_state=42), strategy="recursive", window_length=4)
            pred_ridge, _ = predict_end_quarter(y_fit, ridge_rec, fh_quarters, threshold, X=X_fit, X_future=X_future)
            end_ridge = first_quarter_below(pred_ridge, threshold) if pred_ridge is not None else None
            results.append(
                {
                    "model": "Ridge recursive (losses + recruiting)",
                    "predicted_end_quarter": str(end_ridge) if end_ridge is not None else "— (not below threshold in 20q)",
                }
            )
        except Exception:
            results.append({"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (fit/predict failed)"})
    else:
        results.append({"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (no recruiting or too short)"})

    if include_details:
        details = {
            "y": y,
            "recruiting": recruiting,
            "threshold": threshold,
            "recent_mean": recent_mean,
            "pred_expo": pred_expo,
            "fitted_expo": fitted_expo,
            "recruiting_forecast": recruiting_forecast,
            "y_fit": y_fit,
            "X_fit": X_fit,
            "pred_sar": pred_sar,
            "pred_ridge": pred_ridge,
            "end_expo": end_expo,
            "end_sar": first_quarter_below(pred_sar, threshold) if pred_sar is not None else None,
            "end_ridge": first_quarter_below(pred_ridge, threshold) if pred_ridge is not None else None,
        }
        return (results, details)
    return results
