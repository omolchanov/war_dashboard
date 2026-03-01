"""
Build a merged quarterly dataset from all pipelines and compute feature correlation.
Run from project root: python -m analysis.run_analysis
Prints top-5 feature pairs by correlation (Pearson).
"""

import numpy as np
import pandas as pd

from utils import load_quarterly_merged


def numeric_features_only(df: pd.DataFrame) -> pd.DataFrame:
    """Return dataframe with only numeric columns (exclude period, year, quarter, source)."""
    exclude = {"period", "year", "quarter", "source"}
    numeric = df.select_dtypes(include=["number"])
    return numeric[[c for c in numeric.columns if c not in exclude]]


def main() -> None:
    print("Loading quarterly data from Losses, Economics, Recruiting pipelines...")
    merged = load_quarterly_merged(verbose=True)
    features = numeric_features_only(merged)
    features = features.dropna(how="all", axis=1)

    # Correlation: top-5 pairs by absolute correlation
    corr = features.corr()
    corr_pairs = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool)).stack().reset_index()
    corr_pairs.columns = ["feature_a", "feature_b", "correlation"]
    corr_pairs["abs_corr"] = corr_pairs["correlation"].abs()
    top5_corr = corr_pairs.nlargest(5, "abs_corr")[["feature_a", "feature_b", "correlation"]].reset_index(drop=True)
    print("Top 5 feature pairs by correlation (Pearson):")
    print(top5_corr.to_string())


if __name__ == "__main__":
    main()
