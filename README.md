# AI Business Investigator

Most BI dashboards are good at telling you *what* happened. They're terrible at telling you *why*.

This project is my attempt at closing that gap — a business intelligence system that doesn't just plot a dip in revenue and call it a day. It flags the anomaly, digs through product/customer/country/time dimensions to find what's actually driving it, runs the numbers through a significance test so you're not chasing noise, and only *then* hands the validated evidence to an LLM to write up a plain-English explanation.

The rule I built this around: **the math decides, the model explains.** Gemini never gets to invent a root cause — it only narrates the evidence that's already been statistically validated.

---

## Live Demo

| Layer | Platform | Link |
|---|---|---|
| Frontend | Vercel | [business-investigator.vercel.app](https://business-investigator.vercel.app) |
| Backend / API | Render | [business-investigator.onrender.com](https://business-investigator.onrender.com) |
| API Docs (Swagger) | Render | [business-investigator.onrender.com/docs](https://business-investigator.onrender.com/docs) |

> Backend is on Render's free tier, so the first request after a while might take 30–50s to wake up. Not a bug, just cold-start economics.

---

## Why I built it this way

Anomaly detection is easy to fake. Throw a z-score on revenue, flag anything outside 3 standard deviations, ship it. The hard part — and the part that actually matters to a business — is the next question: *okay, so what caused it?*

So the pipeline is deliberately split into two halves that don't trust each other blindly:

1. **The analytical core** (deterministic, testable, boring in the best way) — cleans the data, computes KPIs, detects anomalies statistically *and* with an Isolation Forest, drills into which product/customer/country/hour combination is responsible, and runs a t-test to check if the "cause" is actually significant or just coincidence.
2. **The explanation layer** — Gemini gets the validated evidence bundle and writes the human-readable summary. It has no path to hallucinate a cause that isn't backed by numbers, because it never sees raw data — only the conclusions the analytical layer already proved.

This also makes the system honest about forecasting. There's no "AI predicts your revenue" magic — it's XGBoost trained on lag features, rolling averages, and calendar signals, with SHAP explaining exactly which features pushed the prediction up or down.

---

## What it actually does

- CSV / Excel dataset upload, with automated validation and cleaning
- Daily and monthly KPI engine (revenue, AOV, repeat rate, growth, and more)
- Two-layer anomaly detection — rolling z-score + Isolation Forest for multivariate outliers
- Root-cause investigation across product, customer, country, and time, including dimension intersections (e.g. *this customer, buying this product, in this country, at this hour*)
- Statistical validation (t-test, p-values) before anything gets called a "cause"
- 7-day revenue forecasting with XGBoost
- SHAP-based explainability for every forecast
- Evidence-grounded explanations via Gemini
- Exportable PDF investigation reports
- PostgreSQL-backed dataset management
- 27/27 automated tests passing, Gemini calls mocked so CI doesn't depend on a live API key

---

## Architecture

```
CSV / Excel
     │
     ▼
Data Ingestion → Validation & Cleaning → Processed Transaction Data
     │
     ├──────────────► KPI Engine
     │
     └──────────────► Anomaly Detection
                         ├── Statistical (rolling z-score)
                         └── Isolation Forest
                                │
                                ▼
                       Investigation Engine
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          Product       Customer       Country
                                │
                                ▼
                          Time Analysis
                                │
                                ▼
                        Root Cause Ranking
                                │
                                ▼
                     Statistical Validation
                                │
                                ▼
                          Evidence Layer
                                │
                                ▼
                      Gemini Explanation
                                │
                                ▼
                        FastAPI Backend
                                │
                                ▼
                       React Dashboard
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python, FastAPI, Pandas, NumPy, SciPy, Scikit-learn, XGBoost, SHAP, Google Gemini API, ReportLab, PostgreSQL |
| **Frontend** | React, TypeScript, Vite, Recharts, Lucide React |
| **Infra / Deployment** | Docker, Vercel (frontend), Render (backend + Postgres) |
| **Testing** | Pytest |

---

## Project Structure

```
business-investigator/
├── api/                  # FastAPI app (main.py, schemas.py)
├── dashboard/            # React + TypeScript frontend
├── data/                 # raw / processed / sample / uploads
├── evaluation/           # Evaluation results
├── models/
├── notebooks/
├── src/
│   ├── ingestion/
│   ├── cleaning/
│   ├── features/
│   ├── analytics/
│   ├── models/
│   ├── investigation/
│   ├── database/
│   └── utils/
├── tests/
├── docker/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Getting Started

```bash
# clone
git clone https://github.com/<your-username>/business-investigator.git
cd business-investigator

# backend
pip install -r requirements.txt
uvicorn api.main:app --reload

# frontend
cd dashboard
npm install
npm run dev
```

Or skip all of that and just run:

```bash
docker-compose up
```

### Environment Variables

Create a `.env` in the project root (or set the equivalents on Render/Vercel):

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.7-flash
DATABASE_URL=your_postgres_connection_string
```

Never commit real API keys or database credentials.

---

## Dataset

Built and evaluated on the **UCI Online Retail II** transactional dataset.

**Expected columns:** `Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `Price`, `Customer ID`, `Country`

You're not locked into that schema, though — CSV and Excel uploads work directly through the dashboard/API for any dataset that follows the same shape.

---

## Analytics Pipeline

### Data Cleaning
Standardizes types → removes duplicates → flags cancellations/returns → strips invalid/bad-debt adjustments → calculates revenue (`Quantity × Price`) → writes to `data/processed/`.

### KPI Engine
Revenue, orders, customers, units sold, AOV, revenue per customer, new vs. repeat customers, repeat rate, product performance, daily and monthly metrics, growth.

**On the evaluation dataset:**

| KPI | Value |
|---|---|
| Total Revenue | £20,465,198.39 |
| Orders | 45,330 |
| Customers | 5,881 |
| Net Units Sold | 10,886,592 |
| Average Order Value | £451.47 |
| Repeat Customer Rate | 72.35% |

### Anomaly Detection

**Statistical (30-day rolling baseline):**

```
Z-score = (Actual Revenue − Rolling Mean) / Rolling Std Dev
```

Flagged when `|Z-score| ≥ 3`.

| Z-score | Severity |
|---|---|
| < 2 | Normal |
| 2 – < 3 | Medium |
| 3 – < 4 | High |
| ≥ 4 | Critical |

**Multivariate:** Isolation Forest over Revenue, Orders, Customers, AOV, and Units Sold — catches the anomalies a single-metric z-score misses entirely.

### Root Cause Investigation
Breaks the anomaly down by product, customer, country, and time, ranks likely root causes, and checks dimension intersections (e.g. *Customer + Product + Country + Hour*) to catch concentrated events instead of stopping at one flat dimension.

### Statistical Validation
Baseline mean, anomaly revenue, standard deviation, t-statistic, p-value, significance — computed and checked *before* anything reaches the explanation layer.

### Revenue Forecasting (XGBoost)
Predicts `next_7_days_revenue` from calendar features, revenue lags (1/7/14 days), rolling averages, orders, customers, AOV, and repeat-customer rate. Chronological train/test split — no peeking into the future during training.

| Metric | Result |
|---|---|
| Train Rows | 561 |
| Test Rows | 141 |
| MAE | £34,951.32 |
| RMSE | £44,070.47 |
| MAPE | 14.05% |

### SHAP Explainability
Every forecast comes with a breakdown of which features pushed it up or down. No black-box numbers.

### Gemini Explanation Layer

```
Anomaly → Root Cause Analysis → Statistical Validation → Evidence → Gemini → Business Explanation
```

Gemini takes the validated evidence and writes a plain-language summary — what happened, who/what drove it, the supporting evidence, caveats, and suggested next steps. It explains the finding; it doesn't produce it.

---

## Dashboard Walkthrough

1. Open **Overview**, check the KPIs
2. Pick a dataset
3. **Analytics** for revenue/product trends
4. **Anomalies**, filter by severity
5. Click into an anomaly to start an investigation
6. Review root causes, contributions, intersections
7. Read the Gemini explanation
8. Export the investigation as a PDF
9. **Forecast** for the 7-day outlook, evaluation metrics, and SHAP importance

---

## API Endpoints

```
GET  /health
POST /upload
GET  /datasets
GET  /datasets/{dataset_id}
GET  /anomalies/{dataset_id}
GET  /summary/{dataset_id}
GET  /analytics/{dataset_id}
GET  /forecast/{dataset_id}
GET  /investigate/{dataset_id}/{anomaly_date}
GET  /report/{dataset_id}/{anomaly_date}
```

Full interactive docs live at [`/docs`](https://business-investigator.onrender.com/docs) on the deployed backend.

---

## Evaluation

I didn't want to just eyeball whether root-cause detection "seemed right," so I ran controlled synthetic revenue injections (by country, product, and customer) and checked whether the system actually found them:

**Root Cause Detection:**

| Metric | Result |
|---|---|
| Top-1 Accuracy | 100% |
| Top-3 Accuracy | 100% |

**Anomaly Detection** (synthetic injection across 604 evaluated dates):

| Metric | Result |
|---|---|
| Target Detected | ✅ Yes |
| Recall | 100% |
| Precision | 6.25% |
| False Positive Rate | 2.49% |

That precision number looks rough at first glance, and I'm not going to bury it — naturally occurring anomalies were also present in the evaluation window, so the detector was correctly flagging real anomalies that weren't the injected target. Recall and false-positive rate are the numbers that actually matter for "did it catch the thing," and both hold up.

**Forecast Evaluation:** MAE £34,951.32 · RMSE £44,070.47 · MAPE 14.05%

**Automated Tests:** 27 passed / 0 failed — covering statistical validation, anomaly detection, root-cause investigation, XGBoost forecasting, SHAP explainability, and the API. Gemini calls are mocked so the suite never depends on live API availability.

---

## Design Principles

- **Evidence first** — analytical evidence is generated before any AI explanation is written
- **Deterministic core** — KPIs, anomaly scores, contributions, and predictions come from real analytical components, not the LLM
- **Explainability by default** — SHAP explains the forecast, not just the forecast number
- **Clean separation of concerns** — Data → Analytics → ML → Investigation → Evidence → AI Explanation → API → Frontend
- **Evaluation-driven** — the core intelligence is backed by automated tests and controlled-scenario evaluation, not vibes

---

## Project Status

| Component | Status |
|---|---|
| Data Ingestion & Cleaning | ✅ |
| PostgreSQL Integration | ✅ |
| KPI Engine | ✅ |
| Anomaly Detection | ✅ |
| Root Cause Analysis | ✅ |
| Statistical Validation | ✅ |
| XGBoost Forecasting | ✅ |
| SHAP Explainability | ✅ |
| Gemini Explanation | ✅ |
| FastAPI Backend | ✅ |
| React Dashboard | ✅ |
| PDF Reports | ✅ |
| Docker | ✅ |
| Automated Testing | ✅ |

## Roadmap

- User authentication & multi-user workspaces
- Persistent project management
- Advanced AI investigation agents
- Background investigation jobs
- Production-grade cloud deployment & model monitoring
- Automated data-quality monitoring
- Additional datasets & domain-specific anomaly detectors

---

## Author

**Yash Rathi**

📧 rathiyash2005@gmail.com

---

## License

Developed for academic and educational purposes.