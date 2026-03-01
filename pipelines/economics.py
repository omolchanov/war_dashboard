"""
Economics data pipeline.
Fetches Russian economics from IMF WEO and World Bank WDI, builds annual then quarterly DataFrame.
Adds Urals oil price (via Brent from IMF PCPS), balance of trade (World Bank), and budget surplus/deficit (IMF WEO).
"""

import io

import pandas as pd
import requests

from config import REQUEST_TIMEOUT, REQUEST_TIMEOUT_SHORT, YEAR_MAX, YEAR_MIN
from pipelines.base import QuarterlyPipeline


class EconomicsPipeline(QuarterlyPipeline):
    """Fetch and aggregate economics data (annual → quarterly, 2022–2025)."""

    # IMF World Economic Outlook
    IMF_WEO_BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.RES/WEO"
    IMF_COUNTRY = "RUS"
    IMF_START_YEAR = 2020
    # IMF WEO: GGXCNL_NGDP = General government net lending/borrowing (% GDP); negative = deficit
    IMF_INDICATORS = ["NGDP_RPCH", "PCPIPCH", "GGXWDG_NGDP", "GGXCNL_NGDP"]
    IMF_INDICATOR_LABELS = {
        "NGDP_RPCH": "gdp_growth",
        "PCPIPCH": "inflation",
        "GGXWDG_NGDP": "debt_pct_gdp",
        "GGXCNL_NGDP": "budget_balance_pct_gdp",
    }

    # World Bank WDI – exports % GDP, exports/imports in current US$ for balance of trade
    WORLD_BANK_BASE = "https://api.worldbank.org/v2"
    WB_COUNTRY = "RUS"
    WB_DATE_RANGE = "2020:2030"
    WB_EXPORTS_INDICATOR = "NE.EXP.GNFS.ZS"
    WB_EXPORTS_CD = "NE.EXP.GNFS.CD"  # Exports of goods and services (current US$)
    WB_IMPORTS_CD = "NE.IMP.GNFS.CD"  # Imports of goods and services (current US$)

    # Oil price: IMF PCPS via DBnomics (Urals not in PCPS; we use Brent crude $/bbl)
    DBNOMICS_BASE = "https://api.db.nomics.world/v22"
    DBNOMICS_OIL_SERIES = "IMF/PCPS/M.W00.POILBRE.USD"  # Monthly Brent, US Dollars

    def __init__(self, year_min: int = YEAR_MIN, year_max: int = YEAR_MAX):
        self.year_min = year_min
        self.year_max = year_max

    def fetch_imf_weo(self) -> pd.DataFrame:
        """Fetch Russian economics from IMF WEO. Returns annual DataFrame."""
        url = f"{self.IMF_WEO_BASE}/~/*?c[TIME_PERIOD]=ge:{self.IMF_START_YEAR}-01"
        resp = requests.get(url, headers={"Accept": "text/csv"}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), low_memory=False)
        df = df[(df["COUNTRY"] == self.IMF_COUNTRY) & (df["INDICATOR"].isin(self.IMF_INDICATORS))].copy()
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
        url = f"{self.WORLD_BANK_BASE}/country/{self.WB_COUNTRY}/indicator/{self.WB_EXPORTS_INDICATOR}?date={self.WB_DATE_RANGE}&format=json&per_page=500"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT_SHORT)
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

    def fetch_wb_indicator(self, indicator: str) -> pd.DataFrame:
        """Fetch one World Bank indicator for Russia (annual). Returns DataFrame with year and value column."""
        url = f"{self.WORLD_BANK_BASE}/country/{self.WB_COUNTRY}/indicator/{indicator}?date={self.WB_DATE_RANGE}&format=json&per_page=500"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if not data or len(data) < 2:
            return pd.DataFrame()
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
            rows.append({"year": year, "value": value if value is not None else float("nan")})
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).drop_duplicates(subset=["year"]).sort_values("year").reset_index(drop=True)

    def fetch_wb_balance_of_trade(self, verbose: bool = False) -> pd.DataFrame:
        """
        Fetch Russian exports and imports (current US$) from World Bank; return annual balance = exports - imports.
        """
        if verbose:
            print("Fetching World Bank exports (current US$) for balance of trade...")
        df_exp = self.fetch_wb_indicator(self.WB_EXPORTS_CD)
        if verbose:
            print("Fetching World Bank imports (current US$) for balance of trade...")
        df_imp = self.fetch_wb_indicator(self.WB_IMPORTS_CD)
        if df_exp.empty or df_imp.empty:
            return pd.DataFrame(columns=["year", "balance_of_trade"])
        df_exp = df_exp.rename(columns={"value": "exports"})
        df_imp = df_imp.rename(columns={"value": "imports"})
        merged = df_exp.merge(df_imp[["year", "imports"]], on="year", how="outer")
        merged["exports"] = pd.to_numeric(merged["exports"], errors="coerce")
        merged["imports"] = pd.to_numeric(merged["imports"], errors="coerce")
        merged["balance_of_trade"] = merged["exports"] - merged["imports"]
        return merged[["year", "balance_of_trade"]].sort_values("year").reset_index(drop=True)

    def fetch_oil_price_quarterly(self, verbose: bool = False) -> pd.DataFrame:
        """Fetch monthly oil price (Brent from IMF PCPS via DBnomics), aggregate to quarterly average.
        Series is Brent crude $/bbl (Urals is not in IMF PCPS; Brent is used as the oil price series)."""
        try:
            url = f"{self.DBNOMICS_BASE}/series/IMF/PCPS/M.W00.POILBRE.USD?observations=1&format=json"
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            series = data.get("series", {})
            docs = series.get("docs", [])
            if not docs:
                return pd.DataFrame(columns=["period", "urals_oil_price"])
            doc = docs[0]
            periods = doc.get("period_start_day") or doc.get("period") or []
            values = doc.get("value") or []
            if len(periods) != len(values):
                return pd.DataFrame(columns=["period", "urals_oil_price"])
            rows = []
            for p, v in zip(periods, values):
                try:
                    if isinstance(p, str) and len(p) == 7 and p[4] == "-":  # "2022-01"
                        ts = pd.Timestamp(p + "-01")
                    else:
                        ts = pd.Timestamp(p)
                    val = float(v) if v is not None else float("nan")
                    rows.append({"date": ts, "urals_oil_price": val})
                except (ValueError, TypeError):
                    continue
            if not rows:
                return pd.DataFrame(columns=["period", "urals_oil_price"])
            df = pd.DataFrame(rows)
            df = df.dropna(subset=["urals_oil_price"])
            if df.empty:
                return pd.DataFrame(columns=["period", "urals_oil_price"])
            df["period"] = df["date"].dt.to_period("Q").dt.start_time
            q = df.groupby("period", as_index=False)["urals_oil_price"].mean()
            q = q[(q["period"].dt.year >= self.year_min) & (q["period"].dt.year <= self.year_max)]
            return q.sort_values("period").reset_index(drop=True)
        except (requests.RequestException, ValueError, KeyError) as e:
            if verbose:
                print(f"Oil price fetch failed ({e}), skipping.")
            return pd.DataFrame(columns=["period", "urals_oil_price"])

    def build_annual_economics(self, verbose: bool = False) -> pd.DataFrame:
        """Build annual economics: IMF WEO merged with World Bank exports and balance of trade. Filter to year range."""
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
        df_balance = self.fetch_wb_balance_of_trade(verbose=verbose)
        if not df_balance.empty and "balance_of_trade" in df_balance.columns:
            df_annual = df_annual.merge(df_balance[["year", "balance_of_trade"]], on="year", how="left")
        else:
            df_annual["balance_of_trade"] = float("nan")
        # budget_balance_pct_gdp comes from IMF WEO (GGXCNL_NGDP); add if missing
        if "budget_balance_pct_gdp" not in df_annual.columns:
            df_annual["budget_balance_pct_gdp"] = float("nan")
        df_annual = df_annual[(df_annual["year"] >= self.year_min) & (df_annual["year"] <= self.year_max)].sort_values("year").reset_index(drop=True)
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
        """Build annual economics and expand to quarterly (one row per quarter); merge quarterly oil price (average)."""
        df_annual = self.build_annual_economics(verbose=verbose)
        df_quarterly = self.annual_to_quarterly(df_annual)
        if verbose:
            print("Fetching oil price (Brent, IMF PCPS) and aggregating by quarter...")
        df_oil = self.fetch_oil_price_quarterly(verbose=verbose)
        if not df_oil.empty:
            df_quarterly = df_quarterly.merge(df_oil[["period", "urals_oil_price"]], on="period", how="left")
        else:
            df_quarterly["urals_oil_price"] = float("nan")
        return df_quarterly

    def get_quarterly(self, verbose: bool = False) -> pd.DataFrame:
        """Implement QuarterlyPipeline. Returns same as get_grouped_quarterly()."""
        return self.get_grouped_quarterly(verbose=verbose)


if __name__ == "__main__":
    print("Building economics from IMF WEO + World Bank (Russia)...")
    pipeline = EconomicsPipeline()
    df = pipeline.get_grouped_quarterly(verbose=True)
    print(f"Economics DataFrame (quarterly) shape: {df.shape}")
    print(df.to_string())
