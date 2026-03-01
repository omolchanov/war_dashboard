"""
Shared data loader: merge quarterly data from all pipelines.
Used by analysis, prediction, and API.
"""

import pandas as pd

from pipelines import EconomicsPipeline, LossesPipeline, RecruitingPipeline


def load_quarterly_merged(verbose: bool = False) -> pd.DataFrame:
    """Load quarterly data from all pipelines (via get_quarterly) and merge on period."""
    losses = LossesPipeline().get_quarterly(verbose=verbose)
    economics = EconomicsPipeline().get_quarterly(verbose=verbose)
    recruiting = RecruitingPipeline().get_quarterly(verbose=verbose)
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
