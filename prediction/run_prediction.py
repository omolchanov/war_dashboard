"""
Time series prediction CLI: when Russia could stop the war (quarter level).

Uses personnel losses and recruiting data. Three models: (1) Exponential smoothing
on personnel (recruiting in explanation); (2) SARIMAX with recruiting as exogenous;
(3) Recursive reduction (Ridge) with recruiting as exogenous. All report the first
quarter where predicted personnel falls below a threshold.

Run from project root: python -m prediction.run_prediction
  --json  Output only JSON results (used by API for consistency).
"""

import argparse
import json
import sys

import pandas as pd

from prediction.models import get_prediction_results

# Re-export for API: from prediction.run_prediction import get_prediction_results
__all__ = ["get_prediction_results", "main"]


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

    y_min, y_max = float(y.min()), float(y.max())
    y_last = float(y.iloc[-1])
    y_last_4 = y.iloc[-4:] if len(y) >= 4 else y
    recent_avg = float(y_last_4.mean())
    print("  Data the model was fitted on (quarterly Russian personnel losses, 2022–2025):")
    print(f"    Losses range from {y_min:,.0f} to {y_max:,.0f}; last quarter = {y_last:,.0f}.")
    print(
        f"    Recent 4-quarter average ≈ {recent_avg:,.0f}. We define 'war stops' when predicted losses drop below 5% of that: {threshold:,.0f}."
    )

    if recruiting is not None and not recruiting.empty:
        rec_last = float(recruiting.iloc[-1])
        rec_last_4 = recruiting.iloc[-4:] if len(recruiting) >= 4 else recruiting
        rec_avg = float(rec_last_4.mean())
        print("  Recruiting (contracts signed, avg per quarter, same period):")
        print(f"    Last quarter ≈ {rec_last:,.0f}; recent 4-quarter average ≈ {rec_avg:,.0f}.")
        if (
            recruiting_forecast is not None
            and not recruiting_forecast.empty
            and end_period is not None
            and end_period in recruiting_forecast.index
        ):
            rec_at_end = float(recruiting_forecast.loc[end_period])
            print(
                f"    Projected recruiting in the predicted war-end quarter ({end_period}): ≈ {rec_at_end:,.0f} contracts (avg per quarter)."
            )

    try:
        fit = getattr(forecaster, "_fitted_forecaster", None)
        if fit is not None and hasattr(fit, "params"):
            p = fit.params
            init_level = p.get("initial_level")
            init_trend = p.get("initial_trend")
            if init_level is not None and init_trend is not None:
                print(
                    f"    From the fitted curve: the model picks up an initial level of losses around {init_level:,.0f} and an initial trend of about {init_trend:,.0f} per quarter."
                )
                if init_trend > 0:
                    print(
                        "    That trend is positive in the early part of the sample; the model then projects it adjusting downward over the forecast horizon."
                    )
                else:
                    print("    That trend is negative; the model projects continued decline in quarterly losses.")
    except Exception:
        pass

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


def main() -> None:
    print("Loading quarterly data (Losses, Economics, Recruiting)...")
    out = get_prediction_results(verbose=True, include_details=True)
    if not out:
        print("Not enough quarters for forecasting. Need at least 4.")
        return
    results, details = out
    y = details["y"]
    recruiting = details["recruiting"]
    threshold = details["threshold"]
    recent_mean = details["recent_mean"]
    pred_expo = details["pred_expo"]
    fitted_expo = details["fitted_expo"]
    recruiting_forecast = details["recruiting_forecast"]
    pred_sar = details["pred_sar"]
    pred_ridge = details["pred_ridge"]
    X_fit = details["X_fit"]
    y_fit = details["y_fit"]

    print(f"Personnel series: {len(y)} quarters, from {y.index[0]} to {y.index[-1]}")
    if recruiting is not None:
        print(f"Recruiting series: {len(recruiting)} quarters (contracts_signed_avg_per_quarter)")
    print(f"Stop threshold: predicted personnel < {threshold:,.0f} (5% of recent mean {recent_mean:,.0f})")

    end_expo = details["end_expo"]
    explain_exp_smoothing(
        y,
        pred_expo,
        threshold,
        end_expo,
        recent_mean,
        fitted_expo,
        recruiting=recruiting,
        recruiting_forecast=recruiting_forecast,
    )

    end_sar = details["end_sar"]
    _print_model_block(
        "SARIMAX (losses + recruiting)",
        pred_sar,
        threshold,
        end_sar,
        "Uses personnel losses as target and recruiting (contracts signed, avg per quarter) as exogenous regressor; predicts when losses drop below threshold.",
    )

    end_ridge = details["end_ridge"]
    _print_model_block(
        "Ridge recursive (losses + recruiting)",
        pred_ridge,
        threshold,
        end_ridge,
        "Recursive regression: predicts next-quarter losses from lagged losses and current recruiting; uses recruiting forecast for future steps.",
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(pd.DataFrame(results).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output only JSON results (for API)")
    args = parser.parse_args()
    if args.json:
        results = get_prediction_results(verbose=False)
        print(json.dumps({"results": results}))
        sys.exit(0)
    main()
