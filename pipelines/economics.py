"""
Economics data pipeline.
Fetches Russian economics from IMF WEO and World Bank WDI, builds annual then quarterly DataFrame.
"""

import io

import pandas as pd
import requests

from config import YEAR_MAX, YEAR_MIN


class EconomicsPipeline:
    """Fetch and aggregate economics data (annual → quarterly, 2022–2025)."""

    # IMF World Economic Outlook
    IMF_WEO_BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.RES/WEO"
    IMF_COUNTRY = "RUS"
    IMF_START_YEAR = 2020
    IMF_INDICATORS = ["NGDP_RPCH", "PCPIPCH", "GGXWDG_NGDP"]
    IMF_INDICATOR_LABELS = {
        "NGDP_RPCH": "gdp_growth",
        "PCPIPCH": "inflation",
        "GGXWDG_NGDP": "debt_pct_gdp",
    }

    # World Bank WDI – exports % GDP
    WORLD_BANK_BASE = "https://api.worldbank.org/v2"
    WB_COUNTRY = "RUS"
    WB_DATE_RANGE = "2020:2030"
    WB_EXPORTS_INDICATOR = "NE.EXP.GNFS.ZS"

    def __init__(self, year_min: int = YEAR_MIN, year_max: int = YEAR_MAX):
        self.year_min = year_min
        self.year_max = year_max

    def fetch_imf_weo(self) -> pd.DataFrame:
        """Fetch Russian economics from IMF WEO. Returns annual DataFrame."""
        url = (
            f"{self.IMF_WEO_BASE}/~/*"
            f"?c[TIME_PERIOD]=ge:{self.IMF_START_YEAR}-01"
        )
        resp = requests.get(url, headers={"Accept": "text/csv"}, timeout=60)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), low_memory=False)
        df = df[
            (df["COUNTRY"] == self.IMF_COUNTRY)
            & (df["INDICATOR"].isin(self.IMF_INDICATORS))
        ].copy()
        if df.empty:
            return pd.DataFrame()
        df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce")
        df = df.dropna(subset=["year"])
        df["year"] = df["year"].astype(int)
        df["indicator"] = df["INDICATOR"].map(self.IMF_INDICATOR_LABELS)
        df = df.dropna(subset=["indicator"])
        df = df.rename(columns={"OBS_VALUE": "value"})
        pivot = df.pivot(index="year", columns="indicator", values="value").reset_index()
        pivot = pivot.sort_values("year").reset_index(drop=True)
        return pivot

    def fetch_wb_exports(self) -> pd.DataFrame:
        """Fetch Russian exports of goods and services (% of GDP) from World Bank WDI."""
        url = (
            f"{self.WORLD_BANK_BASE}/country/{self.WB_COUNTRY}/indicator/{self.WB_EXPORTS_INDICATOR}"
            f"?date={self.WB_DATE_RANGE}&format=json&per_page=500"
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

    def build_annual_economics(self, verbose: bool = False) -> pd.DataFrame:
        """Build annual economics: IMF WEO merged with World Bank exports. Filter to year range."""
        if verbose:
            print("Fetching IMF WEO (Russia)...")
        df_imf = self.fetch_imf_weo()
        if df_imf.empty:
            raise RuntimeError("No IMF WEO data returned for Russia.")
        if verbose:
            print("Fetching World Bank exports % GDP (Russia)...")
        df_wb = self.fetch_wb_exports()
        if df_wb.empty or "trade_pct_gdp" not in df_wb.columns:
            df_annual = df_imf.copy()
        else:
            df_annual = df_imf.merge(df_wb[["year", "trade_pct_gdp"]], on="year", how="left")
        df_annual = df_annual[
            (df_annual["year"] >= self.year_min) & (df_annual["year"] <= self.year_max)
        ].sort_values("year").reset_index(drop=True)
        return df_annual

    @staticmethod
    def annual_to_quarterly(df_annual: pd.DataFrame) -> pd.DataFrame:
        """Expand annual data to quarterly (Q1–Q4 per year). period = first day of quarter (YYYY-MM-DD)."""
        if df_annual.empty or "year" not in df_annual.columns:
            return pd.DataFrame()
        value_cols = [c for c in df_annual.columns if c != "year"]
        rows = []
        for _, row in df_annual.iterrows():
            y = int(row["year"])
            for q in range(1, 5):
                month = q * 3 - 2
                r = {"period": pd.Timestamp(year=y, month=month, day=1), "year": y}
                for c in value_cols:
                    r[c] = row[c]
                rows.append(r)
        return pd.DataFrame(rows)

    def get_grouped_quarterly(self, verbose: bool = False) -> pd.DataFrame:
        """Build annual economics and expand to quarterly (one row per quarter)."""
        df_annual = self.build_annual_economics(verbose=verbose)
        return self.annual_to_quarterly(df_annual)


if __name__ == "__main__":
    print("Building economics from IMF WEO + World Bank (Russia)...")
    pipeline = EconomicsPipeline()
    df = pipeline.get_grouped_quarterly(verbose=True)
    print(f"Economics DataFrame (quarterly) shape: {df.shape}")
    print(df.to_string())
