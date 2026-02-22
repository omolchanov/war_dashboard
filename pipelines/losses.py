"""
Losses data pipeline.
Fetches Russian losses from russian-casualties.in.ua and groups by month.
"""

import pandas as pd
import requests

from config import YEAR_MAX, YEAR_MIN


class LossesPipeline:
    """Fetch and aggregate losses data by month (2022–2025)."""

    LOSSES_DATA_URL = "https://russian-casualties.in.ua/api/v1/data/json/daily"

    def __init__(self, year_min: int = YEAR_MIN, year_max: int = YEAR_MAX):
        self.year_min = year_min
        self.year_max = year_max

    def fetch_raw(self) -> dict:
        """Fetch raw daily loss data from russian-casualties.in.ua API."""
        resp = requests.get(self.LOSSES_DATA_URL, timeout=30)
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
            rows.append({
                "date": pd.to_datetime(norm, format="%Y-%m-%d"),
                "personnel": day.get("personnel", 0),
                "uav": day.get("uav", 0),
                "air_defense_systems": day.get("aaws", 0),
            })
        df = pd.DataFrame(rows)
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def get_grouped_monthly(self) -> pd.DataFrame:
        """Fetch, parse, and group by month. Restrict to year_min–year_max."""
        raw = self.fetch_raw()
        df = self.parse_to_dataframe(raw)
        df = df.copy()
        df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
        loss_cols = [c for c in df.columns if c not in ("date", "month")]
        grouped = df.groupby("month", as_index=False)[loss_cols].sum()
        grouped = grouped[
            (grouped["month"].dt.year >= self.year_min)
            & (grouped["month"].dt.year <= self.year_max)
        ].reset_index(drop=True)
        return grouped


if __name__ == "__main__":
    pipeline = LossesPipeline()
    print("Fetching loss data...")
    raw = pipeline.fetch_raw()
    print(f"Fetched {len(raw.get('data', {}))} daily records")
    df = pipeline.parse_to_dataframe(raw)
    print(f"Losses DataFrame shape: {df.shape}")
    print(df.head(10).to_string())
    print("Done.")
