"""
Base interface for quarterly data pipelines.
All pipelines return DataFrames with a 'period' column (first day of quarter).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


class QuarterlyPipeline(ABC):
    """Abstract base for pipelines that produce quarterly DataFrames with 'period' column."""

    @abstractmethod
    def get_quarterly(self, verbose: bool = False) -> "pd.DataFrame":
        """Return quarterly DataFrame with 'period' (first day of quarter). May include year, quarter, metrics."""
        ...
