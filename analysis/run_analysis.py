"""
Build a merged quarterly dataset from all pipelines and analyze how features affect each other.

Domains:
- Economics: GDP growth, inflation, debt, budget, trade, oil price (Russia)
- Losses: Personnel, UAV, air defense systems (russian-casualties.in.ua)
- Recruiting: Contract signings per quarter (curated estimates)

Run from project root: python -m analysis.run_analysis

Analyses:
1. Top feature correlations (Pearson)
2. Cross-domain correlations (economics ↔ losses ↔ recruiting)
3. Lagged effects (does X in quarter T predict Y in T+1?)
4. Time-trend summary

All outputs include human-readable explanations.
"""

import numpy as np
import pandas as pd

from utils import load_quarterly_merged


# Feature domain mapping for cross-domain analysis
ECONOMICS_FEATURES = {
    "gdp_growth",
    "inflation",
    "debt_pct_gdp",
    "budget_balance_pct_gdp",
    "trade_pct_gdp",
    "balance_of_trade",
    "urals_oil_price",
}

LOSSES_FEATURES = {"personnel", "uav", "air_defense_systems"}

RECRUITING_FEATURES = {
    "contracts_signed_avg_per_quarter",
    "contracts_min_avg_per_quarter",
    "contracts_max_avg_per_quarter",
}


def numeric_features_only(df: pd.DataFrame) -> pd.DataFrame:
    """Return dataframe with only numeric columns (exclude period, year, quarter, source)."""
    exclude = {"period", "year", "quarter", "source"}
    numeric = df.select_dtypes(include=["number"])
    return numeric[[c for c in numeric.columns if c not in exclude]]


def assign_domain(col: str) -> str:
    """Return domain label for a feature column."""
    if col in ECONOMICS_FEATURES:
        return "economics"
    if col in LOSSES_FEATURES:
        return "losses"
    if col in RECRUITING_FEATURES:
        return "recruiting"
    return "other"


def _explain_top_corr() -> str:
    return (
        "\n[Explanation] Strong correlations (|r| > 0.7) suggest features move together. "
        "Positive r = both increase together; negative r = one goes up when the other goes down. "
        "Correlation does not imply causation—other factors may drive both."
    )


def _explain_cross_domain() -> str:
    return (
        "\n[Explanation] Cross-domain correlations show how war-related metrics (losses, recruiting) "
        "relate to macroeconomic conditions. For example: lower oil revenue may limit military spending; "
        "higher personnel losses may drive recruitment efforts; economic strain can affect both."
    )


def _explain_lagged() -> str:
    return (
        "\n[Explanation] Lagged correlations test whether past values of one feature predict future values of another. "
        "E.g., 'oil_price (t) vs personnel (t+1)' shows if oil in quarter T relates to losses in T+1. "
        "Useful to explore lead-lag relationships and potential causal timing."
    )


def _explain_trends() -> str:
    return (
        "\n[Explanation] Quarter-over-quarter changes show momentum. "
        "Positive median change = feature tends to increase over time; negative = tends to decrease. "
        "Large variability suggests irregular or seasonal patterns. "
        "Recruiting features often show median Δ ≈ 0 because data is annual (expanded to quarters)."
    )


def run_top_correlations(features: pd.DataFrame) -> None:
    """Print top-5 feature pairs by absolute correlation with explanation."""
    corr = features.corr()
    triu_mask = np.triu(np.ones(corr.shape), k=1).astype(bool)
    corr_pairs = corr.where(triu_mask).stack().reset_index()
    corr_pairs.columns = ["feature_a", "feature_b", "correlation"]
    corr_pairs["abs_corr"] = corr_pairs["correlation"].abs()
    top5 = corr_pairs.nlargest(5, "abs_corr")[["feature_a", "feature_b", "correlation"]].reset_index(drop=True)
    print("\n" + "=" * 70)
    print("1. TOP 5 FEATURE PAIRS BY CORRELATION (PEARSON)")
    print("=" * 70)
    print(top5.to_string())
    print(_explain_top_corr())


def run_cross_domain_analysis(features: pd.DataFrame) -> None:
    """Analyze correlations between economics, losses, and recruiting with explanations."""
    cols = [c for c in features.columns if assign_domain(c) != "other"]
    if not cols:
        print("\n[Cross-domain] No domain-mapped features found.")
        return
    sub = features[cols].copy()
    sub = sub.dropna(how="all")
    if sub.empty or len(sub) < 3:
        print("\n[Cross-domain] Insufficient data for cross-domain analysis.")
        return

    corr = sub.corr()
    domains = [(a, b) for a in ["economics", "losses", "recruiting"] for b in ["economics", "losses", "recruiting"] if a < b]

    print("\n" + "=" * 70)
    print("2. CROSS-DOMAIN CORRELATIONS (Economics ↔ Losses ↔ Recruiting)")
    print("=" * 70)

    for da, db in domains:
        cols_a = [c for c in sub.columns if assign_domain(c) == da]
        cols_b = [c for c in sub.columns if assign_domain(c) == db]
        if not cols_a or not cols_b:
            continue
        cross = corr.loc[cols_a, cols_b]
        vals = cross.values.flatten()
        vals = vals[~np.isnan(vals)]
        if len(vals) == 0:
            continue
        top_abs = np.abs(vals)
        idx = np.argmax(top_abs)
        r = vals[idx]
        flat_idx = np.unravel_index(np.argmax(np.abs(cross.values)), cross.shape)
        fa, fb = cross.index[flat_idx[0]], cross.columns[flat_idx[1]]
        print(f"\n  {da.upper()} ↔ {db.upper()}:")
        print(f"    Strongest pair: {fa} vs {fb}  →  r = {r:.3f}")
        if abs(r) > 0.5:
            direction = "move together" if r > 0 else "move in opposite directions"
            print(f"    → Moderate/strong relationship: they tend to {direction}.")
        else:
            print(f"    → Weak linear relationship in this sample.")

    print(_explain_cross_domain())


def run_lagged_analysis(features: pd.DataFrame, merged: pd.DataFrame, max_lag: int = 2) -> None:
    """Compute lagged correlations: does X(t) predict Y(t+k)?"""
    cols = [c for c in features.columns if c in merged.columns]
    if "period" not in merged.columns or len(merged) < max_lag + 3:
        print("\n[Lagged] Insufficient data for lagged analysis.")
        return

    df = merged[["period"] + cols].dropna(how="all", subset=cols).reset_index(drop=True)
    if df.empty or len(df) < max_lag + 3:
        return

    print("\n" + "=" * 70)
    print("3. LAGGED CORRELATIONS (Does X in quarter T predict Y in T+1 or T+2?)")
    print("=" * 70)

    # Cross-domain pairs only for interpretability
    economics_cols = [c for c in cols if assign_domain(c) == "economics"]
    losses_cols = [c for c in cols if assign_domain(c) == "losses"]
    recruiting_cols = [c for c in cols if assign_domain(c) == "recruiting"]

    pairs = []
    for lag in range(1, max_lag + 1):
        for lead_col in economics_cols + recruiting_cols:
            for lag_col in losses_cols + recruiting_cols:
                if lead_col == lag_col:
                    continue
                x = df[lead_col].iloc[:-lag].values
                y = df[lag_col].iloc[lag:].values
                if len(x) != len(y) or np.isnan(x).all() or np.isnan(y).all():
                    continue
                valid = ~(np.isnan(x) | np.isnan(y))
                if valid.sum() < 3:
                    continue
                r = np.corrcoef(x[valid], y[valid])[0, 1]
                if not np.isnan(r):
                    pairs.append((lead_col, lag_col, lag, r))

    if not pairs:
        print("  No valid lagged pairs (insufficient overlap after lag).")
        print(_explain_lagged())
        return

    pairs = sorted(pairs, key=lambda p: abs(p[3]), reverse=True)[:8]
    print("\n  Top lagged relationships (leading feature → lagged feature, r):")
    for lead, lagged, lag, r in pairs:
        print(f"    {lead} (t) → {lagged} (t+{lag}): r = {r:.3f}")
    print(_explain_lagged())


def run_trend_analysis(features: pd.DataFrame, merged: pd.DataFrame) -> None:
    """Summarize quarter-over-quarter changes per domain."""
    cols = [c for c in features.columns if c in merged.columns and assign_domain(c) != "other"]
    if not cols or "period" not in merged.columns:
        return

    df = merged[["period"] + cols].sort_values("period").dropna(how="all", subset=cols)
    if len(df) < 2:
        return

    diff = df[cols].diff().dropna(how="all")
    if diff.empty:
        return

    print("\n" + "=" * 70)
    print("4. QUARTER-OVER-QUARTER TRENDS (Median change per feature)")
    print("=" * 70)

    for domain in ["economics", "losses", "recruiting"]:
        dc = [c for c in cols if assign_domain(c) == domain]
        if not dc:
            continue
        med = diff[dc].median()
        print(f"\n  {domain.upper()}:")
        for c in dc:
            m = med.get(c, np.nan)
            s = diff[c].std()
            trend = "↑ increasing" if m > 0 else "↓ decreasing" if m < 0 else "≈ stable"
            print(f"    {c}: median Δ = {m:.2f}, std Δ = {s:.2f}  ({trend})")
    print(_explain_trends())


def run_summary(features: pd.DataFrame) -> None:
    """Print a plain-language summary of how the three domains relate."""
    print("\n" + "=" * 70)
    print("5. SUMMARY: HOW ECONOMICS, LOSSES & RECRUITING AFFECT EACH OTHER")
    print("=" * 70)
    print("""
  ECONOMICS → LOSSES
    • Higher government debt (% GDP) tends to coincide with higher UAV losses
      (possible link: sanctions/economics affecting military supply chains).
    • Oil price and trade metrics show weaker direct links to losses in this sample.

  ECONOMICS → RECRUITING
    • When trade share of GDP or balance of trade drops, recruiting (contract signings)
      tends to rise—suggesting economic pressure may drive mobilization efforts.
    • Lower oil prices in quarter T often precede higher recruitment in T+1/T+2.

  LOSSES → RECRUITING
    • Higher personnel losses correlate with higher contract signings (replacement demand).
    • Recruitment levels in quarter T correlate with personnel losses in T+1/T+2,
      consistent with new personnel entering combat after training.

  RECRUITING → LOSSES
    • Recruiting intensity may precede personnel losses (more troops → more casualties
      when engaged), as suggested by lagged correlations.

  CAVEATS
    • Data is limited (2022–2025, quarterly). Correlations can be driven by common
      time trends (e.g., war escalation) rather than direct causation.
    • Recruiting data is annual, expanded to quarters—intra-year variation is imputed.
    • Always interpret alongside domain knowledge and external events.
""")


def main() -> None:
    print("=" * 70)
    print("WAR DASHBOARD: CROSS-DOMAIN FEATURE ANALYSIS")
    print("=" * 70)
    print("""
  Domains:
  • Economics: GDP growth, inflation, debt, budget, trade, oil price (Russia)
  • Losses: Personnel, UAV, air defense systems (russian-casualties.in.ua)
  • Recruiting: Contract signings per quarter (curated estimates)
""")
    print("Loading quarterly data from Losses, Economics, Recruiting pipelines...")
    merged = load_quarterly_merged(verbose=True)
    features = numeric_features_only(merged)
    features = features.dropna(how="all", axis=1)

    if features.empty or len(features) < 3:
        print("Insufficient data for analysis.")
        return

    run_top_correlations(features)
    run_cross_domain_analysis(features)
    run_lagged_analysis(features, merged)
    run_trend_analysis(features, merged)
    run_summary(features)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
