"""
WarDashboard Data Pipeline
Fetches Russian losses data, builds a pandas DataFrame, and plots histograms.
Data source: LOSSES_DATA_URL (russian-casualties.in.ua daily API).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests

LOSSES_DATA_URL = "https://russian-casualties.in.ua/api/v1/data/json/daily"
FIGURES_DIR = Path(__file__).parent / "output/images/mod_analysis"


def fetch_raw_data() -> dict:
    """Fetch raw daily loss data from russian-casualties.in.ua API."""
    resp = requests.get(LOSSES_DATA_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_to_dataframe(raw: dict) -> pd.DataFrame:
    """Parse russian-casualties.in.ua API response into a pandas DataFrame. Filter from Feb 2022 onward."""
    data = raw.get("data", {})
    rows = []
    for date_str, day in data.items():
        # date_str is "YYYY.MM.DD"
        if not date_str or not day:
            continue
        # Filter: from 2022-02-01 onward
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


def _monthly_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Group daily data by month and sum losses."""
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    loss_cols = [c for c in df.columns if c not in ("date", "month")]
    return df.groupby("month", as_index=False)[loss_cols].sum()


def plot_histograms(df: pd.DataFrame) -> None:
    """Plot losses by month (bar charts) for key metrics and save to figures/."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    monthly = _monthly_totals(df)

    metrics = [
        ("personnel", "Personnel"),
        ("uav", "UAVs"),
        ("air_defense_systems", "Air Defense Systems"),
    ]

    for col, label in metrics:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(monthly["month"], monthly[col], width=20, edgecolor="black", alpha=0.8)
        ax.set_xlabel("Month")
        ax.set_ylabel(f"{label} (total losses)")
        ax.set_title(f"{label} losses by month")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        out_path = FIGURES_DIR / f"hist_{col}.png"
        plt.savefig(out_path, dpi=100)
        plt.close()
        print(f"Saved: {out_path}")


def main() -> None:
    print("Fetching loss data...")
    raw = fetch_raw_data()
    n_days = len(raw.get("data", {}))
    print(f"Fetched {n_days} daily records")

    print("Parsing and filtering from Feb 2022...")
    df = parse_to_dataframe(raw)
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns {df.info()}")
    print(df.head(10).to_string())

    print("\nPlotting histograms...")
    plot_histograms(df)
    print("Done.")


if __name__ == "__main__":
    main()
