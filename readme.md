# WarDashboard

API, pipelines, analysis, and prediction for war-related data (losses, economics, recruiting). Predicts when the war could end (quarter level) using time series models.

## Data sources

### Economics

| Metric | Source | Aggregation |
|--------|--------|-------------|
| GDP growth, inflation, debt % GDP | IMF World Economic Outlook (WEO) | Annual → repeated per quarter |
| Trade % GDP | World Bank WDI (NE.EXP.GNFS.ZS) | Annual → repeated per quarter |
| **Urals oil price** | IMF Primary Commodity Prices (PCPS) via [DBnomics](https://db.nomics.world/IMF/PCPS) — *Brent crude* $/bbl (Urals not in PCPS) | Monthly → **quarterly average** |
| **Balance of trade** | World Bank WDI: exports (NE.EXP.GNFS.CD) − imports (NE.IMP.GNFS.CD), current US$ | Annual → repeated per quarter |
| **Budget surplus/deficit** | IMF WEO: GGXCNL_NGDP — General government net lending/borrowing (% of GDP); negative = deficit | Annual → repeated per quarter |

### Losses

| Metric | Source | Aggregation |
|--------|--------|-------------|
| Personnel, UAV, air defense systems | [russian-casualties.in.ua](https://russian-casualties.in.ua) API | Daily → **quarterly sum** |

### Recruiting (Russia army contract recruitment)

| Metric | Source | Aggregation |
|--------|--------|-------------|
| Contract signings (estimate, min, max) | Curated CSV from IStories budget analysis and published reports (no public API) | Annual → **quarterly average** (annual ÷ 4) |

Data file: `data/russia_recruiting.csv`. Quarterly output columns: `contracts_signed_avg_per_quarter`, `contracts_min_avg_per_quarter`, `contracts_max_avg_per_quarter`.

---

## Configuration

Optional environment variables (prefix `WAR_DASHBOARD_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `YEAR_MIN` | 2022 | Start year for data filter |
| `YEAR_MAX` | 2025 | End year for data filter |
| `REQUEST_TIMEOUT` | 60 | HTTP timeout (seconds) for external API calls |
| `REQUEST_TIMEOUT_SHORT` | 30 | Shorter timeout for quick requests |

---

## Project structure

```
WarDashboard/
  config.py                 # Year range, timeouts (env overrides)
  pyproject.toml            # Project metadata, ruff/mypy config
  data/
    russia_recruiting.csv   # Curated Russia contract recruitment estimates (annual)
  utils/
    __init__.py
    data_loader.py          # Shared load_quarterly_merged (merge all pipelines)
    serialization.py        # DataFrame → JSON records (ISO dates, NaN→null)
  api/
    __init__.py
    app.py                  # FastAPI app, routes, v1 router, exception handlers
    schemas.py              # Pydantic response models
  pipelines/
    __init__.py
    base.py                 # QuarterlyPipeline ABC (get_quarterly interface)
    losses.py               # LossesPipeline (quarterly)
    economics.py            # EconomicsPipeline (quarterly)
    recruiting.py           # RecruitingPipeline (annual → quarterly average)
  analysis/
    run_analysis.py         # Correlation: top-5 feature pairs (quarterly merged data)
    README.md
  prediction/
    data.py                 # get_personnel_series, get_recruiting_series
    models.py               # get_prediction_results, model logic (no print)
    run_prediction.py       # CLI entry point, prints results
    README.md
  tests/
    test_api.py
```

## Run the server

From project root:

```bash
pip install -r requirements.txt
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

Base URL: **http://localhost:8000**

**Run analysis (correlation):**
```bash
python -m analysis.run_analysis
```

**Run prediction (war-end quarter, prints explanations):**
```bash
python -m prediction.run_prediction
```

---

## Endpoints

| Endpoint      | URL | Description |
|---------------|-----|-------------|
| **Root**      | http://localhost:8000/ | API info and list of endpoints |
| **Losses**    | http://localhost:8000/losses | Quarterly grouped losses (period, year, quarter, personnel, uav, air_defense_systems) |
| **Economics** | http://localhost:8000/economics | Quarterly economics (gdp_growth, inflation, trade_pct_gdp, debt_pct_gdp, balance_of_trade, budget_balance_pct_gdp, urals_oil_price) |
| **Recruiting**| http://localhost:8000/recruiting | Quarterly recruiting (contracts_signed_avg_per_quarter, etc.; curated annual ÷ 4) |
| **Prediction**| http://localhost:8000/prediction | Prediction results: list of `{ model, predicted_end_quarter }` (Exponential smoothing, SARIMAX, Ridge; uses losses + recruiting) |
| **v1 API**    | http://localhost:8000/v1/ | Versioned API: `/v1/losses`, `/v1/economics`, `/v1/recruiting`, `/v1/prediction` (same data, Pydantic-validated responses) |

---

## How to fetch

**Browser:** Open the URL (e.g. http://localhost:8000/losses).

**curl:**
```bash
curl http://localhost:8000/losses
curl http://localhost:8000/economics
curl http://localhost:8000/recruiting
curl http://localhost:8000/prediction
```

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/losses"
Invoke-RestMethod -Uri "http://localhost:8000/economics"
Invoke-RestMethod -Uri "http://localhost:8000/recruiting"
Invoke-RestMethod -Uri "http://localhost:8000/prediction"
```

**Python:**
```python
import requests
r = requests.get("http://localhost:8000/losses")
losses = r.json()
r = requests.get("http://localhost:8000/economics")
economics = r.json()
r = requests.get("http://localhost:8000/recruiting")
recruiting = r.json()
r = requests.get("http://localhost:8000/prediction")
prediction = r.json()  # {"results": [{"model": "...", "predicted_end_quarter": "..."}, ...]}
```

---

## Response format

- **`/losses`** — JSON array of objects: `period` (YYYY-MM-DD, first day of quarter), `year`, `quarter`, `personnel`, `uav`, `air_defense_systems` (quarterly sums from Feb 2022).
- **`/economics`** — JSON array of objects: `period`, `year`, `gdp_growth`, `inflation`, `trade_pct_gdp`, `debt_pct_gdp`, `balance_of_trade`, `budget_balance_pct_gdp` (surplus/deficit % GDP; negative = deficit), `urals_oil_price`. Sources: IMF WEO + World Bank (Russia); oil from IMF PCPS via DBnomics (Brent $/bbl, quarterly avg).
- **`/recruiting`** — JSON array of objects: `period` (YYYY-MM-DD, first day of quarter), `year`, `quarter`, `contracts_signed_avg_per_quarter`, `contracts_min_avg_per_quarter`, `contracts_max_avg_per_quarter`, `source`. Quarterly average = annual total ÷ 4 (curated data).
- **`/prediction`** — JSON object: `results` (array of objects). Each object: `model` (string), `predicted_end_quarter` (string, e.g. `"2028Q3"` or `"— (not below threshold in 20q)"`). Models: Exponential smoothing, SARIMAX (losses + recruiting), Ridge recursive (losses + recruiting).
