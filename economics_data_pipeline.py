"""
Economics Data Pipeline
Fetches Russian economics from World Bank WDI (GDP, inflation, trade, debt),
builds a DataFrame, and plots histograms.

Central government debt as % of GDP
How to read it
- Low (e.g. &lt; 30%): Debt is modest relative to the economy; fiscal space is typically larger.
- Moderate (e.g. 30–60%): Common for many countries; sustainability depends on growth and interest rates.
- High (e.g. &gt; 60–100%+): Debt burden is heavy; more sensitivity to interest rates and investor confidence

GDP growth (annual %)
How to read it
- Positive (e.g. +4%): Economy is expanding; output and usually employment are rising.
- Negative (e.g. −1.5%): Economy is shrinking; recession.
- Zero: Roughly flat compared to the previous year.

Consumer price inflation (annual %)
A Consumer Price Index (CPI) – the cost of a typical basket of goods and services (food, housing, transport, etc.).
How to read it
- Low (e.g. 0–3%): Prices fairly stable; common target for many central banks.
- Moderate (e.g. 3–8%): Noticeable but often manageable; can reflect strong demand or supply shocks.
- High (e.g. 10%+): Erodes living standards and savings; often needs policy action.

Exports of goods and services as % of GDP
How to read it
- Low (e.g. &lt; 20%): Economy is more domestic‑oriented.
- Medium (e.g. 20–40%): Moderate openness to trade; exports are a noticeable share of the economy.
- High (e.g. &gt; 40%): Economy is very export‑dependent.

Data source: World Bank WDI API (annual). Data is expanded to quarters for display.
"""

import pandas as pd
import requests

WORLD_BANK_BASE = "https://api.worldbank.org/v2"
WB_COUNTRY = "RUS"
WB_DATE_RANGE = "2022:2030"
# WDI indicator codes: GDP growth %, Inflation (CPI) %, Exports % GDP, Central govt debt % GDP


WB_INDICATORS = [
    "NY.GDP.MKTP.KD.ZG",   # GDP growth (annual %)
    "FP.CPI.TOTL.ZG",      # Inflation, consumer prices (annual %)
    "NE.EXP.GNFS.ZS",      # Exports of goods and services (% of GDP)
    "GC.DOD.TOTL.GD.ZS",   # Central government debt (% of GDP)
]
WB_INDICATOR_LABELS = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth",
    "FP.CPI.TOTL.ZG": "inflation",
    "NE.EXP.GNFS.ZS": "trade_pct_gdp",
    "GC.DOD.TOTL.GD.ZS": "debt_pct_gdp",
}

# Display frequency: "quarterly" expands annual values to Q1–Q4 per year; "annual" keeps one bar per year.
FREQUENCY = "quarterly"


def fetch_wb_economics() -> list:
    """Fetch Russian economics from World Bank WDI (GDP, inflation, trade, debt). Returns list of records."""
    all_records = []
    for ind in WB_INDICATORS:
        url = (
            f"{WORLD_BANK_BASE}/country/{WB_COUNTRY}/indicator/{ind}"
            f"?date={WB_DATE_RANGE}&format=json&per_page=500"
        )
        page = 1
        while True:
            resp = requests.get(f"{url}&page={page}", timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data or len(data) < 2:
                break
            meta, records = data[0], data[1]
            if not records:
                break
            all_records.extend(records)
            if page >= meta.get("pages", 1):
                break
            page += 1
    return all_records


def parse_wb_to_dataframe(records: list) -> pd.DataFrame:
    """Parse World Bank API records into a DataFrame: one row per year, columns = economic metrics."""
    rows = []
    for r in records:
        ind_id = r.get("indicator", {}).get("id")
        if ind_id not in WB_INDICATOR_LABELS:
            continue
        date_str = r.get("date", "")
        value = r.get("value")
        if not date_str:
            continue
        rows.append({
            "year": int(date_str),
            "indicator": WB_INDICATOR_LABELS[ind_id],
            "value": value if value is not None else float("nan"),
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Pivot: index=year, columns=indicator, values=value
    out = df.pivot(index="year", columns="indicator", values="value").reset_index()
    out = out.sort_values("year").reset_index(drop=True)
    return out


def annual_to_quarterly(df_annual: pd.DataFrame) -> pd.DataFrame:
    """
    Expand annual WDI data to quarterly: each year becomes 4 rows (Q1–Q4) with the same value.
    WDI does not publish quarterly data for Russia; this allows comparison with quarterly loss data.
    """
    if df_annual.empty or "year" not in df_annual.columns:
        return pd.DataFrame()
    value_cols = [c for c in df_annual.columns if c != "year"]
    rows = []
    for _, row in df_annual.iterrows():
        y = int(row["year"])
        for q in range(1, 5):
            r = {"period": f"{y}-Q{q}", "year": y}
            for c in value_cols:
                r[c] = row[c]
            rows.append(r)
    return pd.DataFrame(rows)


def main() -> None:
    print("Fetching World Bank economics (Russia)...")
    wb_records = fetch_wb_economics()
    print(f"Fetched {len(wb_records)} WDI records")

    print("Parsing economics to DataFrame (annual)...")
    df_annual = parse_wb_to_dataframe(wb_records)
    print(f"Economics DataFrame (annual) shape: {df_annual.shape}")
    print(df_annual.to_string())

    if FREQUENCY == "quarterly":
        print("\nExpanding to quarterly (same annual value per quarter)...")
        df_quarterly = annual_to_quarterly(df_annual)
        print(f"Economics DataFrame (quarterly) shape: {df_quarterly.shape}")
        print(df_quarterly.to_string())
    print("Done.")


if __name__ == "__main__":
    main()
