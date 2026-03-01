"""
Losses data pipeline.
Fetches Russian losses from russian-casualties.in.ua and groups by quarter (same as economics/recruiting).
"""

import pandas as pd
import requests

from config import REQUEST_TIMEOUT_SHORT, YEAR_MAX, YEAR_MIN
from pipelines.base import QuarterlyPipeline


class LossesPipeline(QuarterlyPipeline):
    """Fetch and aggregate losses data by quarter (2022–2025)."""

    LOSSES_DATA_URL = "https://russian-casualties.in.ua/api/v1/data/json/daily"

    def __init__(self, year_min: int = YEAR_MIN, year_max: int = YEAR_MAX):
        self.year_min = year_min
        self.year_max = year_max

    def fetch_raw(self) -> dict:
        """Fetch raw daily loss data from russian-casualties.in.ua API."""
        resp = requests.get(self.LOSSES_DATA_URL, timeout=REQUEST_TIMEOUT_SHORT)
        resp.raise_for_status()
        return resp.json()

    def parse_to_dataframe(self, raw: dict) -> pd.DataFrame:
        """Parse API response into a DataFrame. Filter from Feb 2022 onward."""
        data = raw.get("data", {})
        rows = []
        for date_str, day in data.items():
            if not date_str or not day:
                continue
            norm = date_str.replace(".", "-")
            if norm < "2022-02-01":
                continue
            rows.append(
                {
                    "date": pd.to_datetime(norm, format="%Y-%m-%d"),
                    "personnel": day.get("personnel", 0),
                    "uav": day.get("uav", 0),
                    "air_defense_systems": day.get("aaws", 0),
                }
            )
        df = pd.DataFrame(rows)
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def get_grouped_quarterly(self) -> pd.DataFrame:
        """Fetch, parse, and group by quarter. One row per quarter: period (first day), year, quarter, loss sums.
        Restrict to year_min–year_max. Same structure as economics/recruiting."""
        raw = self.fetch_raw()
        df = self.parse_to_dataframe(raw)
        df = df.copy()
        df["quarter"] = df["date"].dt.quarter
        df["year"] = df["date"].dt.year
        df["period"] = df["date"].dt.to_period("Q").dt.to_timestamp()
        loss_cols = [c for c in df.columns if c not in ("date", "period", "year", "quarter")]
        grouped = df.groupby(["period", "year", "quarter"], as_index=False)[loss_cols].sum()
        grouped = grouped[(grouped["year"] >= self.year_min) & (grouped["year"] <= self.year_max)].reset_index(drop=True)
        return grouped

    def get_quarterly(self, verbose: bool = False) -> pd.DataFrame:
        """Implement QuarterlyPipeline. Returns same as get_grouped_quarterly()."""
        return self.get_grouped_quarterly()


if __name__ == "__main__":
    pipeline = LossesPipeline()
    print("Fetching loss data...")
    raw = pipeline.fetch_raw()
    print(f"Fetched {len(raw.get('data', {}))} daily records")
    df = pipeline.parse_to_dataframe(raw)
    print(f"Losses parsed shape: {df.shape}")
    q = pipeline.get_grouped_quarterly()
    print(f"Losses quarterly shape: {q.shape}")
    print(q.to_string())
    print("Done.")
