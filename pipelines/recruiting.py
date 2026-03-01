"""
Russia army recruiting data pipeline.
Uses curated estimates (no public API). Data from IStories budget analysis and published reports.
"""

from pathlib import Path

import pandas as pd

from config import YEAR_MAX, YEAR_MIN
from pipelines.base import QuarterlyPipeline


class RecruitingPipeline(QuarterlyPipeline):
    """Load and filter Russia contract recruitment estimates by year (2022–2025)."""

    # Curated CSV next to project root
    _DATA_DIR = Path(__file__).resolve().parent.parent / "data"
    RECRUITING_CSV = _DATA_DIR / "russia_recruiting.csv"

    def __init__(self, year_min: int = YEAR_MIN, year_max: int = YEAR_MAX):
        self.year_min = year_min
        self.year_max = year_max

    def load_recruiting(self) -> pd.DataFrame:
        """Load recruiting data from CSV and filter to year range."""
        if not self.RECRUITING_CSV.exists():
            return pd.DataFrame(columns=["year", "contracts_signed", "contracts_min", "contracts_max", "source"])
        df = pd.read_csv(self.RECRUITING_CSV, dtype={"source": str})
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df = df.dropna(subset=["year"])
        df["year"] = df["year"].astype(int)
        df = df[(df["year"] >= self.year_min) & (df["year"] <= self.year_max)].sort_values("year").reset_index(drop=True)
        return df

    def get_recruiting_annual(self) -> pd.DataFrame:
        """Return annual recruiting estimates for the configured year range."""
        return self.load_recruiting()

    # Numeric count columns to split across quarters/months (source is copied as-is)
    _COUNT_COLS = ["contracts_signed", "contracts_min", "contracts_max"]
    # Quarterly output uses average-per-quarter column names (annual ÷ 4)
    _QUARTERLY_AVG_SUFFIX = "_avg_per_quarter"

    @staticmethod
    def _annual_to_quarterly(df_annual: pd.DataFrame) -> pd.DataFrame:
        """Expand annual to quarterly: one row per quarter, counts = annual ÷ 4 (quarterly average)."""
        if df_annual.empty or "year" not in df_annual.columns:
            return pd.DataFrame()
        rows = []
        for _, row in df_annual.iterrows():
            y = int(row["year"])
            for q in range(1, 5):
                month = q * 3 - 2
                r = {"period": pd.Timestamp(year=y, month=month, day=1), "year": y, "quarter": q}
                for c in df_annual.columns:
                    if c == "year":
                        continue
                    if c in RecruitingPipeline._COUNT_COLS:
                        val = row[c]
                        avg_key = c + RecruitingPipeline._QUARTERLY_AVG_SUFFIX
                        r[avg_key] = val / 4 if pd.notna(val) else float("nan")
                    else:
                        r[c] = row[c]
                rows.append(r)
        return pd.DataFrame(rows)

    @staticmethod
    def _annual_to_monthly(df_annual: pd.DataFrame) -> pd.DataFrame:
        """Expand annual to monthly: one row per month, counts divided by 12 (sum = annual)."""
        if df_annual.empty or "year" not in df_annual.columns:
            return pd.DataFrame()
        rows = []
        for _, row in df_annual.iterrows():
            y = int(row["year"])
            for m in range(1, 13):
                r = {"period": pd.Timestamp(year=y, month=m, day=1), "year": y, "month": m}
                for c in df_annual.columns:
                    if c == "year":
                        continue
                    if c in RecruitingPipeline._COUNT_COLS:
                        val = row[c]
                        r[c] = val / 12 if pd.notna(val) else float("nan")
                    else:
                        r[c] = row[c]
                rows.append(r)
        return pd.DataFrame(rows)

    def get_recruiting_quarterly(self) -> pd.DataFrame:
        """Return recruiting by quarter: quarterly average (annual total ÷ 4). Columns use _avg_per_quarter suffix."""
        df_annual = self.load_recruiting()
        return self._annual_to_quarterly(df_annual)

    def get_quarterly(self, verbose: bool = False) -> pd.DataFrame:
        """Implement QuarterlyPipeline. Returns same as get_recruiting_quarterly()."""
        return self.get_recruiting_quarterly()

    def get_recruiting_monthly(self) -> pd.DataFrame:
        """Return recruiting by month (derived from annual: each year's total ÷ 12 per month)."""
        df_annual = self.load_recruiting()
        return self._annual_to_monthly(df_annual)


if __name__ == "__main__":
    print("Loading Russia recruiting data (curated)...")
    pipeline = RecruitingPipeline()
    df = pipeline.get_recruiting_quarterly()
    print(f"Recruiting DataFrame (quarterly average) shape: {df.shape}")
    print(df.to_string())
