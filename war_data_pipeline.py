"""
WarDashboard Data Pipeline
Fetches Ukrainian MoD Russian losses data, builds a pandas DataFrame,
and plots histograms of loss metrics.
Data source: rus-losses-tracker (combat.fyi) - aggregates Ukrainian MoD daily reports.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests

# Data source: Ukrainian MoD losses via rus-losses-tracker (trusted mirror)
# https://combat.fyi | https://github.com/Larzs/rus-losses-tracker
DATA_URL = "https://cdn.jsdelivr.net/gh/larzs/rus-losses-tracker@master/public/list.JSON"
FIGURES_DIR = Path(__file__).parent / "output/images/mod_analysis"


def fetch_raw_data() -> list[dict]:
    """Fetch raw loss data from CDN (Ukrainian MoD / General Staff reports)."""
    resp = requests.get(DATA_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_to_dataframe(raw: list[dict]) -> pd.DataFrame:
    """Parse raw JSON into a pandas DataFrame. Filter from Feb 2022 onward."""
    rows = []
    for entry in raw:
        date_str = entry.get("date")
        if not date_str:
            continue
        # Filter: from 2022-02-01 onward
        if date_str < "2022-02-01":
            continue
        losses = entry.get("losses", {})
        rows.append({
            "date": pd.to_datetime(date_str),
            "personnel": losses.get("personnel", 0),
            "tanks": losses.get("tanks", 0),
            "apv": losses.get("apv", 0),
            "artillery_units": losses.get("artillery_units", 0),
            "mlrs": losses.get("mlrs", 0),
            "air_defense_systems": losses.get("air_defense_systems", 0),
            "planes": losses.get("planes", 0),
            "helicopters": losses.get("helicopters", 0),
            "boats_and_warships": losses.get("boats_and_warships", 0),
            "submarines": losses.get("submarines", 0),
            "uav": losses.get("uav", 0),
            "special_equipment": losses.get("special_equipment", 0),
            "vehicles_and_fuel_tanks": losses.get("vehicles_and_fuel_tanks", 0),
            "cruise_missiles": losses.get("cruise_missiles", 0),
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
        ("tanks", "Tanks"),
        ("apv", "Armored Personnel Vehicles"),
        ("artillery_units", "Artillery Units"),
        ("uav", "UAVs"),
        ("vehicles_and_fuel_tanks", "Vehicles & Fuel Tanks"),
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
    print("Fetching Ukrainian MoD losses data...")
    raw = fetch_raw_data()
    print(f"Fetched {len(raw)} daily records")

    print("Parsing and filtering from Feb 2022...")
    df = parse_to_dataframe(raw)
    print(f"DataFrame shape: {df.shape}")
    print(df.head(10).to_string())

    print("\nPlotting histograms...")
    plot_histograms(df)
    print("Done.")


if __name__ == "__main__":
    main()
