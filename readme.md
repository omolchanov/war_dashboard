# WarDashboard API – How to fetch endpoints

## Data sources (economics)

| Metric | Source | Aggregation |
|--------|--------|-------------|
| GDP growth, inflation, debt % GDP | IMF World Economic Outlook (WEO) | Annual → repeated per quarter |
| Trade % GDP | World Bank WDI (NE.EXP.GNFS.ZS) | Annual → repeated per quarter |
| **Urals oil price** | IMF Primary Commodity Prices (PCPS) via [DBnomics](https://db.nomics.world/IMF/PCPS) — *Brent crude* $/bbl (Urals not in PCPS) | Monthly → **quarterly average** |
| **Balance of trade** | World Bank WDI: exports (NE.EXP.GNFS.CD) − imports (NE.IMP.GNFS.CD), current US$ | Annual → repeated per quarter |
| **Budget surplus/deficit** | IMF WEO: GGXCNL_NGDP — General government net lending/borrowing (% of GDP); negative = deficit | Annual → repeated per quarter |

---

## Project structure

```
WarDashboard/
  config.py                 # YEAR_MIN, YEAR_MAX (shared)
  utils/                    # Helpers
    __init__.py
    serialization.py        # DataFrame → JSON records (ISO dates, NaN→null)
  api/                      # API package
    __init__.py
    app.py                  # FastAPI app and routes
  pipelines/                # Pipelines package (one file per pipeline)
    __init__.py
    losses.py               # LossesPipeline
    economics.py            # EconomicsPipeline
  tests/
    test_api.py
```

## Run the server

```bash
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Base URL: **http://localhost:8000**

---

## Endpoints

| Endpoint   | URL                     | Description |
|-----------|-------------------------|-------------|
| **Root**  | http://localhost:8000/  | API info and list of endpoints |
| **Losses**| http://localhost:8000/losses   | Monthly grouped losses (personnel, uav, air_defense_systems) |
| **Economics** | http://localhost:8000/economics | Quarterly grouped economics (gdp_growth, inflation, trade_pct_gdp, debt_pct_gdp, balance_of_trade, budget_balance_pct_gdp, urals_oil_price) |

---

## How to fetch

**Browser:** Open the URL (e.g. http://localhost:8000/losses).

**curl:**
```bash
curl http://localhost:8000/losses
curl http://localhost:8000/economics
```

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/losses"
Invoke-RestMethod -Uri "http://localhost:8000/economics"
```

**Python:**
```python
import requests
r = requests.get("http://localhost:8000/losses")
losses = r.json()
r = requests.get("http://localhost:8000/economics")
economics = r.json()
```

---

## Response format

- **`/losses`** — JSON array of objects: `month` (YYYY-MM-DD, first day of month), `personnel`, `uav`, `air_defense_systems` (monthly totals from Feb 2022).
- **`/economics`** — JSON array of objects: `period`, `year`, `gdp_growth`, `inflation`, `trade_pct_gdp`, `debt_pct_gdp`, `balance_of_trade`, `budget_balance_pct_gdp` (surplus/deficit % GDP; negative = deficit), `urals_oil_price`. Sources: IMF WEO + World Bank (Russia); oil from IMF PCPS via DBnomics (Brent $/bbl, quarterly avg); balance of trade = exports − imports (current US$); budget = IMF WEO net lending/borrowing (% of GDP).
