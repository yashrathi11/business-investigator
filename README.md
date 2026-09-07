# AI Business Investigator

**An end-to-end AI-powered Business Intelligence & Investigation platform** that detects unusual business behavior, identifies likely root causes, validates findings statistically, forecasts revenue, and generates evidence-grounded explanations — powered by Google Gemini.

> Something unusual happened in the business. What happened, why did it happen, and what should we investigate next?

The analytical engine finds and validates evidence **first**. Gemini is only used afterward — to turn validated evidence into a clear, human-readable explanation.

---

## 🚀 Live Demo

| Layer | Platform | Link |
|---|---|---|
| Frontend | Vercel | `<add your Vercel URL>` |
| Backend / API | Render | `<add your Render URL>` |
| API Docs (Swagger) | Render | `<Render URL>/docs` |

---

## ✨ Key Features

- 📁 CSV / Excel dataset upload
- 🧹 Automated data validation & cleaning
- 📊 Business KPI engine (daily & monthly analytics)
- 🚨 Statistical + multivariate (Isolation Forest) anomaly detection
- 🔍 Root-cause investigation across product, customer, country & time
- 🧩 Dimension-intersection analysis (e.g. Customer + Product + Country + Hour)
- 📈 Statistical significance testing (t-test, p-values)
- 🔮 XGBoost-powered revenue forecasting
- 🧠 SHAP explainability for forecast models
- 🤖 Evidence-grounded Gemini explanations
- 🖨️ Exportable PDF investigation reports
- 🗂️ Dataset management with a PostgreSQL backend
- 🧪 Automated test suite (27/27 passing)

---

## 🏗️ How It Works

```
CSV / Excel
     │
     ▼
Data Ingestion → Validation & Cleaning → Processed Transaction Data
     │
     ├──────────────► KPI Engine
     │
     └──────────────► Anomaly Detection
                         ├── Statistical Detection
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

## 🧰 Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python, FastAPI, Pandas, NumPy, SciPy, Scikit-learn, XGBoost, SHAP, Google Gemini API, ReportLab, PostgreSQL |
| **Frontend** | React, TypeScript, Vite, Recharts, Lucide React |
| **Infra / Deployment** | Docker, Vercel (frontend), Render (backend + Postgres) |
| **Testing** | Pytest |

---

## 📂 Project Structure

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

## 🔑 Environment Variables

Create a `.env` (or configure the equivalent secrets on Render/Vercel):

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.7-flash
DATABASE_URL=your_postgres_connection_string
```

> Never commit real API keys or database credentials to GitHub.

---

## 📊 Dataset

Built and evaluated on the **UCI Online Retail II** transactional dataset.

**Expected columns:**
`Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `Price`, `Customer ID`, `Country`

CSV and Excel uploads are also supported directly through the dashboard/API.

---

## 🧮 Analytics Pipeline

### Data Cleaning
Standardizes types → removes duplicates → flags cancellations/returns → removes invalid/bad-debt adjustments → calculates revenue (`Quantity × Price`) → saves to `data/processed/`.

### KPI Engine
Revenue, orders, customers, units sold, AOV, revenue per customer, new/repeat customers, repeat rate, product performance, daily & monthly metrics, growth.

**Evaluated dataset results:**

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

**Multivariate:** Isolation Forest over Revenue, Orders, Customers, AOV, and Units Sold.

### Root Cause Investigation
Analyzes product, customer, country, and time contributions, then ranks root causes and checks dimension intersections (e.g. *Customer + Product + Country + Hour*) to surface concentrated events rather than isolated dimensions.

### Statistical Validation
Baseline mean, anomaly revenue, standard deviation, t-statistic, p-value, and significance — validated before the explanation step.

### Revenue Forecasting (XGBoost)
Predicts `next_7_days_revenue` using calendar features, revenue lags (1/7/14 days), rolling averages, orders, customers, AOV, and repeat-customer rate, with a chronological train/test split.

| Metric | Result |
|---|---|
| Train Rows | 561 |
| Test Rows | 141 |
| MAE | £34,951.32 |
| RMSE | £44,070.47 |
| MAPE | 14.05% |

### SHAP Explainability
Explains which forecast features drive predictions — no black-box forecasting.

### Gemini Explanation Layer

```
Anomaly → Root Cause Analysis → Statistical Validation → Evidence → Gemini → Business Explanation
```

Gemini turns validated evidence into a plain-language explanation covering the event, main contributors, supporting evidence, caveats, and suggested next actions. **The LLM explains — it doesn't decide.**

---

## 🖥️ Dashboard Workflow

1. Open **Overview** and review KPIs
2. Select a dataset
3. Open **Analytics** to inspect revenue/product trends
4. Open **Anomalies** and filter by severity
5. Select an anomaly and start an investigation
6. Review root causes, contributions, and intersections
7. Read the Gemini explanation
8. Export the investigation report as PDF
9. Open **Forecast** to view the 7-day forecast, evaluation metrics, and SHAP importance

---

## 🔌 API Endpoints

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

Full interactive docs are available at `/docs` on the deployed backend.

---

## ✅ Evaluation

**Root Cause Detection** — controlled synthetic revenue injections (country, product, customer):

| Metric | Result |
|---|---|
| Top-1 Accuracy | 100% |
| Top-3 Accuracy | 100% |

**Anomaly Detection** — controlled synthetic injection across 604 evaluated dates:

| Metric | Result |
|---|---|
| Target Detected | ✅ Yes |
| Recall | 100% |
| Precision | 6.25% |
| False Positive Rate | 2.49% |

> Precision is reported transparently — naturally occurring anomalies were also present during the evaluation window.

**Forecast Evaluation:** MAE £34,951.32 · RMSE £44,070.47 · MAPE 14.05%

**Automated Tests:** `27 passed / 0 failed` — covering statistical validation, anomaly detection, root-cause investigation, XGBoost forecasting, SHAP explainability, and the API. Gemini calls are mocked in tests so the suite doesn't depend on live API availability.

---

## 🧱 Architecture Principles

- **Evidence first** — analytical evidence is generated before any AI explanation
- **Deterministic core** — KPIs, anomaly scores, contributions, and model predictions come from dedicated analytical components, not the LLM
- **Explainability** — SHAP explains forecast behavior
- **Separation of concerns** — Data → Analytics → ML → Investigation → Evidence → AI Explanation → API → Frontend
- **Evaluation-driven** — core intelligence components are covered by automated and controlled-scenario testing

---

## 📌 Project Status

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

---

## 🔭 Roadmap

- User authentication & multi-user workspaces
- Persistent project management
- Advanced AI investigation agents
- Background investigation jobs
- Production-grade cloud deployment & model monitoring
- Automated data-quality monitoring
- Additional datasets & domain-specific anomaly detectors

---

## 👤 Author

**Yash Rathi**
Computer Science & Engineering
Anand International College of Engineering, Jaipur — Rajasthan Technical University, Kota
Academic Session 2026–2027

---

## 📄 License

Developed for academic and educational purposes.
