"""
Economics Data Pipeline
Fetches Russian economics from IMF World Economic Outlook (WEO) and World Bank WDI,
builds a DataFrame, and plots histograms.

Primary source: IMF WEO API – GDP growth, inflation, general government gross debt % GDP.
Secondary source: World Bank WDI – Exports of goods and services (% of GDP) when available.
Only historical years 2022–2025 are kept (no forward projections).

Central government debt as % of GDP
How to read it
- Low (e.g. < 30%): Debt is modest relative to the economy; fiscal space is typically larger.
- Moderate (e.g. 30–60%): Common for many countries; sustainability depends on growth and interest rates.
- High (e.g. > 60–100%+): Debt burden is heavy; more sensitivity to interest rates and investor confidence

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
- Low (e.g. < 20%): Economy is more domestic‑oriented.
- Medium (e.g. 20–40%): Moderate openness to trade; exports are a noticeable share of the economy.
- High (e.g. > 40%): Economy is very export‑dependent.

Data is expanded to quarters for display where needed.
"""

import io
import pandas as pd
import requests

# --- IMF World Economic Outlook (WEO) – primary source, includes 2025+ ---
IMF_WEO_BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.RES/WEO"
IMF_COUNTRY = "RUS"
IMF_START_YEAR = 2020
# WEO subject codes: GDP growth %, Inflation (CPI) %, General government gross debt % GDP
IMF_INDICATORS = ["NGDP_RPCH", "PCPIPCH", "GGXWDG_NGDP"]
IMF_INDICATOR_LABELS = {
    "NGDP_RPCH": "gdp_growth",
    "PCPIPCH": "inflation",
    "GGXWDG_NGDP": "debt_pct_gdp",
}

# --- World Bank WDI – exports % GDP (WDI often lags; IMF WEO has no direct exports % GDP) ---
WORLD_BANK_BASE = "https://api.worldbank.org/v2"
WB_COUNTRY = "RUS"
WB_DATE_RANGE = "2020:2030"
WB_EXPORTS_INDICATOR = "NE.EXP.GNFS.ZS"  # Exports of goods and services (% of GDP)

# Year range: only historical data in this range is kept (2022–2025).
YEAR_MIN = 2022
YEAR_MAX = 2025

# Display frequency: "quarterly" expands annual values to Q1–Q4 per year; "annual" keeps one bar per year.
FREQUENCY = "quarterly"


def fetch_imf_weo() -> pd.DataFrame:
    """Fetch Russian economics from IMF WEO (GDP growth, inflation, debt % GDP). Returns annual DataFrame."""
    # Bulk request: all countries/indicators from start year; we filter to RUS and our indicators.
    url = (
        f"{IMF_WEO_BASE}/~/*"
        f"?c[TIME_PERIOD]=ge:{IMF_START_YEAR}-01"
    )
    resp = requests.get(url, headers={"Accept": "text/csv"}, timeout=60)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), low_memory=False)
    # Standard columns: COUNTRY, INDICATOR, TIME_PERIOD, OBS_VALUE
    df = df[
        (df["COUNTRY"] == IMF_COUNTRY)
        & (df["INDICATOR"].isin(IMF_INDICATORS))
    ].copy()
    if df.empty:
        return pd.DataFrame()
    df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    df["indicator"] = df["INDICATOR"].map(IMF_INDICATOR_LABELS)
    df = df.dropna(subset=["indicator"])
    df = df.rename(columns={"OBS_VALUE": "value"})
    pivot = df.pivot(index="year", columns="indicator", values="value").reset_index()
    pivot = pivot.sort_values("year").reset_index(drop=True)
    return pivot


def fetch_wb_exports() -> pd.DataFrame:
    """Fetch Russian exports of goods and services (% of GDP) from World Bank WDI. One column: year, trade_pct_gdp."""
    url = (
        f"{WORLD_BANK_BASE}/country/{WB_COUNTRY}/indicator/{WB_EXPORTS_INDICATOR}"
        f"?date={WB_DATE_RANGE}&format=json&per_page=500"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data or len(data) < 2:
        return pd.DataFrame(columns=["year", "trade_pct_gdp"])
    records = data[1]
    rows = []
    for r in records:
        date_str = r.get("date", "")
        value = r.get("value")
        if not date_str:
            continue
        try:
            year = int(date_str)
        except ValueError:
            continue
        rows.append({"year": year, "trade_pct_gdp": value if value is not None else float("nan")})
    if not rows:
        return pd.DataFrame(columns=["year", "trade_pct_gdp"])
    out = pd.DataFrame(rows).drop_duplicates(subset=["year"]).sort_values("year").reset_index(drop=True)
    return out


def fetch_wb_economics() -> list:
    """
    Legacy: fetch all four series from World Bank (no 2025).
    Kept for compatibility; prefer fetch_imf_weo + fetch_wb_exports.
    """
    all_records = []
    wb_indicators = [
        "NY.GDP.MKTP.KD.ZG",
        "FP.CPI.TOTL.ZG",
        "NE.EXP.GNFS.ZS",
        "GC.DOD.TOTL.GD.ZS",
    ]
    wb_labels = {
        "NY.GDP.MKTP.KD.ZG": "gdp_growth",
        "FP.CPI.TOTL.ZG": "inflation",
        "NE.EXP.GNFS.ZS": "trade_pct_gdp",
        "GC.DOD.TOTL.GD.ZS": "debt_pct_gdp",
    }
    for ind in wb_indicators:
        u = f"{WORLD_BANK_BASE}/country/{WB_COUNTRY}/indicator/{ind}?date={WB_DATE_RANGE}&format=json&per_page=500"
        page = 1
        while True:
            r = requests.get(f"{u}&page={page}", timeout=30)
            r.raise_for_status()
            data = r.json()
            if not data or len(data) < 2:
                break
            meta, recs = data[0], data[1]
            if not recs:
                break
            all_records.extend(recs)
            if page >= meta.get("pages", 1):
                break
            page += 1
    return all_records


def parse_wb_to_dataframe(records: list) -> pd.DataFrame:
    """Parse World Bank API records into a DataFrame: one row per year, columns = economic metrics."""
    wb_labels = {
        "NY.GDP.MKTP.KD.ZG": "gdp_growth",
        "FP.CPI.TOTL.ZG": "inflation",
        "NE.EXP.GNFS.ZS": "trade_pct_gdp",
        "GC.DOD.TOTL.GD.ZS": "debt_pct_gdp",
    }
    rows = []
    for r in records:
        ind_id = r.get("indicator", {}).get("id")
        if ind_id not in wb_labels:
            continue
        date_str = r.get("date", "")
        value = r.get("value")
        if not date_str:
            continue
        rows.append({
            "year": int(date_str),
            "indicator": wb_labels[ind_id],
            "value": value if value is not None else float("nan"),
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    out = df.pivot(index="year", columns="indicator", values="value").reset_index()
    out = out.sort_values("year").reset_index(drop=True)
    return out


def build_annual_economics() -> pd.DataFrame:
    """
    Build annual economics DataFrame: IMF WEO (gdp_growth, inflation, debt_pct_gdp) merged with
    World Bank exports % GDP. Keeps only historical years in [YEAR_MIN, YEAR_MAX] (2022–2025).
    """
    print("Fetching IMF WEO (Russia)...")
    df_imf = fetch_imf_weo()
    if df_imf.empty:
        raise RuntimeError("No IMF WEO data returned for Russia.")
    print("Fetching World Bank exports % GDP (Russia)...")
    df_wb = fetch_wb_exports()
    if df_wb.empty or "trade_pct_gdp" not in df_wb.columns:
        df_annual = df_imf.copy()
    else:
        df_annual = df_imf.merge(df_wb[["year", "trade_pct_gdp"]], on="year", how="left")
    df_annual = df_annual[
        (df_annual["year"] >= YEAR_MIN) & (df_annual["year"] <= YEAR_MAX)
    ].sort_values("year").reset_index(drop=True)
    return df_annual


def annual_to_quarterly(df_annual: pd.DataFrame) -> pd.DataFrame:
    """
    Expand annual data to quarterly: each year becomes 4 rows (Q1–Q4) with the same value.
    period is the first day of the quarter (same date format as losses month: YYYY-MM-DD).
    """
    if df_annual.empty or "year" not in df_annual.columns:
        return pd.DataFrame()
    value_cols = [c for c in df_annual.columns if c != "year"]
    rows = []
    for _, row in df_annual.iterrows():
        y = int(row["year"])
        for q in range(1, 5):
            # First day of quarter: Q1=01-01, Q2=04-01, Q3=07-01, Q4=10-01 (same format as losses month)
            month = q * 3 - 2
            r = {"period": pd.Timestamp(year=y, month=month, day=1), "year": y}
            for c in value_cols:
                r[c] = row[c]
            rows.append(r)
    return pd.DataFrame(rows)


def main() -> None:
    print("Building economics from IMF WEO + World Bank (Russia)...")
    df_annual = build_annual_economics()
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
