"""
WarDashboard Data Pipeline
Fetches Russian losses data and builds a pandas DataFrame.
Data source: LOSSES_DATA_URL (russian-casualties.in.ua daily API).
"""

import pandas as pd
import requests

LOSSES_DATA_URL = "https://russian-casualties.in.ua/api/v1/data/json/daily"


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


def main() -> None:
    print("Fetching loss data...")
    raw = fetch_raw_data()
    n_days = len(raw.get("data", {}))
    print(f"Fetched {n_days} daily records")

    print("Parsing and filtering from Feb 2022...")
    df = parse_to_dataframe(raw)
    print(f"Losses DataFrame shape: {df.shape}")
    print(df.head(10).to_string())
    print("Done.")


if __name__ == "__main__":
    main()
