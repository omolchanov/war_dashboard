"""
Time series prediction: when Russia could stop the war (quarter level).

Uses personnel losses and recruiting data. Three models: (1) Exponential smoothing
on personnel (recruiting in explanation); (2) SARIMAX with recruiting as exogenous;
(3) Recursive reduction (Ridge) with recruiting as exogenous. All report the first
quarter where predicted personnel falls below a threshold.

Run from project root: python -m prediction.run_prediction
"""

import sys
from pathlib import Path

# Run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from pipelines import EconomicsPipeline, LossesPipeline, RecruitingPipeline

from sktime.forecasting.exp_smoothing import ExponentialSmoothing
from sktime.forecasting.sarimax import SARIMAX
from sktime.forecasting.compose import make_reduction
from sklearn.linear_model import Ridge


def load_quarterly_merged(verbose: bool = False) -> pd.DataFrame:
    """Load quarterly data from all pipelines and merge on period."""
    losses = LossesPipeline().get_grouped_quarterly()
    economics = EconomicsPipeline().get_grouped_quarterly(verbose=verbose)
    recruiting = RecruitingPipeline().get_recruiting_quarterly()
    df = economics.merge(
        losses.drop(columns=["year", "quarter"], errors="ignore"),
        on="period",
        how="outer",
    )
    df = df.merge(
        recruiting.drop(columns=["year", "quarter", "source"], errors="ignore"),
        on="period",
        how="outer",
    )
    return df.sort_values("period").reset_index(drop=True)


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


def _print_model_block(
    name: str,
    pred: pd.Series | None,
    threshold: float,
    end_period,
    description: str,
) -> None:
    """Print a short block for a model (e.g. SARIMAX, Ridge): description, path, predicted end quarter."""
    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)
    print(f"  {description}")
    print(f"  Stop threshold: personnel < {threshold:,.0f}.")
    if pred is not None and not pred.empty:
        print("  Projected personnel losses (first 10 quarters):")
        for i in range(min(10, len(pred))):
            p = pred.iloc[i]
            below = "  <-- below threshold" if p < threshold else ""
            print(f"    {pred.index[i]}: {p:,.0f}{below}")
        if end_period is not None:
            v = float(pred.loc[end_period])
            print(f"  => Predicted war end quarter: {end_period} (projected losses ≈ {v:,.0f})")
        else:
            print("  => No predicted war end quarter within 20 quarters.")
    else:
        print("  (No forecast.)")


def explain_exp_smoothing(
    y: pd.Series,
    pred: pd.Series | None,
    threshold: float,
    end_period,
    recent_mean: float,
    forecaster,
    recruiting: pd.Series | None = None,
    recruiting_forecast: pd.Series | None = None,
) -> None:
    """Print data-contextual explanation (personnel + recruiting), no generic model theory."""
    print("\n" + "=" * 70)
    print("Exponential smoothing (personnel losses and recruiting)")
    print("=" * 70)
    if pred is None or pred.empty:
        print("  (Model fit or predict failed.)")
        return

    # Personnel data we fitted on
    y_min, y_max = float(y.min()), float(y.max())
    y_last = float(y.iloc[-1])
    y_last_4 = y.iloc[-4:] if len(y) >= 4 else y
    recent_avg = float(y_last_4.mean())
    print("  Data the model was fitted on (quarterly Russian personnel losses, 2022–2025):")
    print(f"    Losses range from {y_min:,.0f} to {y_max:,.0f}; last quarter = {y_last:,.0f}.")
    print(f"    Recent 4-quarter average ≈ {recent_avg:,.0f}. We define 'war stops' when predicted losses drop below 5% of that: {threshold:,.0f}.")

    # Recruiting data (same quarters)
    if recruiting is not None and not recruiting.empty:
        rec_last = float(recruiting.iloc[-1])
        rec_last_4 = recruiting.iloc[-4:] if len(recruiting) >= 4 else recruiting
        rec_avg = float(rec_last_4.mean())
        print("  Recruiting (contracts signed, avg per quarter, same period):")
        print(f"    Last quarter ≈ {rec_last:,.0f}; recent 4-quarter average ≈ {rec_avg:,.0f}.")
        if recruiting_forecast is not None and not recruiting_forecast.empty and end_period is not None and end_period in recruiting_forecast.index:
            rec_at_end = float(recruiting_forecast.loc[end_period])
            print(f"    Projected recruiting in the predicted war-end quarter ({end_period}): ≈ {rec_at_end:,.0f} contracts (avg per quarter).")

    # Fitted curve in context of this series
    try:
        fit = getattr(forecaster, "_fitted_forecaster", None)
        if fit is not None and hasattr(fit, "params"):
            p = fit.params
            init_level = p.get("initial_level")
            init_trend = p.get("initial_trend")
            if init_level is not None and init_trend is not None:
                print(f"    From the fitted curve: the model picks up an initial level of losses around {init_level:,.0f} and an initial trend of about {init_trend:,.0f} per quarter.")
                if init_trend > 0:
                    print("    That trend is positive in the early part of the sample; the model then projects it adjusting downward over the forecast horizon.")
                else:
                    print("    That trend is negative; the model projects continued decline in quarterly losses.")
    except Exception:
        pass

    # Forecast path
    print("  Projected quarterly personnel losses (first 10 quarters):")
    for i in range(min(10, len(pred))):
        p = pred.iloc[i]
        below = "  <-- first quarter below stop threshold" if p < threshold else ""
        print(f"    {pred.index[i]}: {p:,.0f}{below}")
    if recruiting_forecast is not None and not recruiting_forecast.empty:
        print("  Projected recruiting (contracts signed, avg per quarter, same horizon):")
        for i in range(min(10, len(recruiting_forecast))):
            r = recruiting_forecast.iloc[i]
            print(f"    {recruiting_forecast.index[i]}: {r:,.0f}")

    if end_period is not None:
        first_below_val = float(pred.loc[end_period])
        print(
            f"  The first quarter where projected losses fall below the stop threshold ({threshold:,.0f}) is {end_period} (projected losses ≈ {first_below_val:,.0f})."
        )
        print(f"  => Predicted war end quarter: {end_period}")
    else:
        print("  Projected losses stay above the threshold for all 20 quarters we forecast.")
        print("  => No predicted war end quarter within the 20-quarter horizon.")


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


def get_prediction_results(verbose: bool = False) -> list[dict]:
    """
    Run all prediction models (Exponential smoothing, SARIMAX, Ridge recursive).
    Returns list of dicts with keys: model (str), predicted_end_quarter (str).
    No printing. Uses losses and recruiting data from pipelines.
    """
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
            expo_rec = ExponentialSmoothing(trend="add", seasonal="add", sp=4)
            expo_rec.fit(recruiting)
            recruiting_forecast = expo_rec.predict(fh=fh)
            X_future = recruiting_forecast.to_frame("recruiting")
        except Exception:
            pass

    y_fit, X_fit = _align_y_X(y, recruiting)
    results = []

    # 1. Exponential smoothing
    expo = ExponentialSmoothing(trend="add", seasonal="add", sp=4)
    pred_expo, _ = predict_end_quarter(y, expo, fh_quarters, threshold)
    end_expo = first_quarter_below(pred_expo, threshold) if pred_expo is not None else None
    results.append({
        "model": "Exponential smoothing",
        "predicted_end_quarter": str(end_expo) if end_expo is not None else "— (not below threshold in 20q)",
    })

    # 2. SARIMAX
    if X_fit is not None and X_future is not None and len(X_fit) >= 6:
        try:
            sarimax = SARIMAX(order=(1, 0, 0), seasonal_order=(0, 0, 0, 4), trend="c")
            pred_sar, _ = predict_end_quarter(y_fit, sarimax, fh_quarters, threshold, X=X_fit, X_future=X_future)
            end_sar = first_quarter_below(pred_sar, threshold) if pred_sar is not None else None
            results.append({
                "model": "SARIMAX (losses + recruiting)",
                "predicted_end_quarter": str(end_sar) if end_sar is not None else "— (not below threshold in 20q)",
            })
        except Exception:
            results.append({"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (fit/predict failed)"})
    else:
        results.append({"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (no recruiting or too short)"})

    # 3. Ridge recursive
    if X_fit is not None and X_future is not None and len(y_fit) >= 6:
        try:
            ridge_rec = make_reduction(Ridge(alpha=1.0), strategy="recursive", window_length=4)
            pred_ridge, _ = predict_end_quarter(y_fit, ridge_rec, fh_quarters, threshold, X=X_fit, X_future=X_future)
            end_ridge = first_quarter_below(pred_ridge, threshold) if pred_ridge is not None else None
            results.append({
                "model": "Ridge recursive (losses + recruiting)",
                "predicted_end_quarter": str(end_ridge) if end_ridge is not None else "— (not below threshold in 20q)",
            })
        except Exception:
            results.append({"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (fit/predict failed)"})
    else:
        results.append({"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (no recruiting or too short)"})

    return results


def main() -> None:
    print("Loading quarterly data (Losses, Economics, Recruiting)...")
    merged = load_quarterly_merged(verbose=True)
    y = get_personnel_series(merged)
    recruiting = get_recruiting_series(merged)
    if len(y) < 4:
        print("Not enough quarters for forecasting. Need at least 4.")
        return
    print(f"Personnel series: {len(y)} quarters, from {y.index[0]} to {y.index[-1]}")
    if recruiting is not None:
        print(f"Recruiting series: {len(recruiting)} quarters (contracts_signed_avg_per_quarter)")

    recent_mean = float(y.rolling(min(8, len(y))).mean().dropna().iloc[-1])
    threshold = recent_mean * 0.05
    fh_quarters = 20
    fh = list(range(1, fh_quarters + 1))
    print(f"Stop threshold: predicted personnel < {threshold:,.0f} (5% of recent mean {recent_mean:,.0f})")

    # Recruiting forecast (used as future exog for SARIMAX and Ridge)
    recruiting_forecast = None
    X_future = None
    if recruiting is not None and len(recruiting) >= 4:
        try:
            expo_rec = ExponentialSmoothing(trend="add", seasonal="add", sp=4)
            expo_rec.fit(recruiting)
            recruiting_forecast = expo_rec.predict(fh=fh)
            X_future = recruiting_forecast.to_frame("recruiting")
        except Exception:
            pass

    y_fit, X_fit = _align_y_X(y, recruiting)
    results = []

    # 1. Exponential smoothing (personnel only; recruiting in explanation)
    expo = ExponentialSmoothing(trend="add", seasonal="add", sp=4)
    pred_expo, fitted_expo = predict_end_quarter(y, expo, fh_quarters, threshold)
    end_expo = first_quarter_below(pred_expo, threshold) if pred_expo is not None else None
    results.append({
        "model": "Exponential smoothing",
        "predicted_end_quarter": str(end_expo) if end_expo is not None else "— (not below threshold in 20q)",
    })
    explain_exp_smoothing(
        y, pred_expo, threshold, end_expo, recent_mean, fitted_expo,
        recruiting=recruiting,
        recruiting_forecast=recruiting_forecast,
    )

    # 2. SARIMAX: personnel ~ ARIMA + recruiting (exog)
    if X_fit is not None and X_future is not None and len(X_fit) >= 6:
        try:
            sarimax = SARIMAX(order=(1, 0, 0), seasonal_order=(0, 0, 0, 4), trend="c")
            pred_sar, _ = predict_end_quarter(y_fit, sarimax, fh_quarters, threshold, X=X_fit, X_future=X_future)
            end_sar = first_quarter_below(pred_sar, threshold) if pred_sar is not None else None
            results.append({
                "model": "SARIMAX (losses + recruiting)",
                "predicted_end_quarter": str(end_sar) if end_sar is not None else "— (not below threshold in 20q)",
            })
            _print_model_block("SARIMAX (losses + recruiting)", pred_sar, threshold, end_sar, "Uses personnel losses as target and recruiting (contracts signed, avg per quarter) as exogenous regressor; predicts when losses drop below threshold.")
        except Exception:
            results.append({"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (fit/predict failed)"})
            _print_model_block("SARIMAX (losses + recruiting)", None, threshold, None, "Fit or predict failed (e.g. short series or numerical issue).")
    else:
        results.append({"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (no recruiting or too short)"})
        _print_model_block("SARIMAX (losses + recruiting)", None, threshold, None, "Skipped: need aligned recruiting and enough history.")

    # 3. Recursive reduction (Ridge): personnel from lags + recruiting
    if X_fit is not None and X_future is not None and len(y_fit) >= 6:
        try:
            ridge_rec = make_reduction(Ridge(alpha=1.0), strategy="recursive", window_length=4)
            pred_ridge, _ = predict_end_quarter(y_fit, ridge_rec, fh_quarters, threshold, X=X_fit, X_future=X_future)
            end_ridge = first_quarter_below(pred_ridge, threshold) if pred_ridge is not None else None
            results.append({
                "model": "Ridge recursive (losses + recruiting)",
                "predicted_end_quarter": str(end_ridge) if end_ridge is not None else "— (not below threshold in 20q)",
            })
            _print_model_block("Ridge recursive (losses + recruiting)", pred_ridge, threshold, end_ridge, "Recursive regression: predicts next-quarter losses from lagged losses and current recruiting; uses recruiting forecast for future steps.")
        except Exception:
            results.append({"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (fit/predict failed)"})
            _print_model_block("Ridge recursive (losses + recruiting)", None, threshold, None, "Fit or predict failed.")
    else:
        results.append({"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (no recruiting or too short)"})
        _print_model_block("Ridge recursive (losses + recruiting)", None, threshold, None, "Skipped: need aligned recruiting and enough history.")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(pd.DataFrame(results).to_string(index=False))


if __name__ == "__main__":
    main()
