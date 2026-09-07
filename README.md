AI Business Investigator
An end-to-end AI-powered Business Intelligence and Investigation platform that detects unusual business behavior, identifies likely root causes, validates findings with statistics and machine learning, forecasts revenue, and generates evidence-grounded business explanations.

1. What Problem Does It Solve?
The system answers a practical business question:

Something unusual happened in the business. What happened, why did it happen, and what should we investigate next?

The analytical engine finds and validates evidence first. Gemini is used afterward to convert validated evidence into a human-readable explanation.

2. How the System Works
CSV / Excel
     |
     v
Data Ingestion
     |
     v
Data Validation & Cleaning
     |
     v
Processed Transaction Data
     |
     +-----------------------------+
     |                             |
     v                             v
KPI Engine                  Anomaly Detection
                                   |
                         +---------+---------+
                         |                   |
                         v                   v
                  Statistical         Isolation Forest
                   Detection
                         |                   |
                         +---------+---------+
                                   |
                                   v
                         Investigation Engine
                                   |
                  +----------------+----------------+
                  |                |                |
                  v                v                v
             Product          Customer          Country
            Analysis          Analysis         Analysis
                  |                |                |
                  +----------------+----------------+
                                   |
                                   v
                             Time Analysis
                                   |
                                   v
                          Root Cause Ranking
                                   |
                                   v
                         Statistical Validation
                                   |
                                   v
                            Evidence Layer
                                   |
                                   v
                         Gemini Explanation
                                   |
                                   v
                            FastAPI Backend
                                   |
                                   v
                           React Dashboard
3. Main Features
CSV / Excel dataset upload

Data validation and cleaning

Business KPI calculation

Daily and monthly analytics

Statistical revenue anomaly detection

Multivariate anomaly detection using Isolation Forest

Product, customer, country, and time contribution analysis

Root-cause ranking and dimension intersection analysis

Statistical significance testing

XGBoost revenue forecasting

SHAP explainability

Evidence-grounded Gemini explanations

Investigation reports and PDF export

Dataset management

FastAPI REST API

Interactive React dashboard

Dockerized backend

Automated testing

Controlled evaluation

4. Technology Stack
Backend
Python, FastAPI, Pandas, NumPy, SciPy, Scikit-learn, XGBoost, SHAP, Google Gemini API, ReportLab, PostgreSQL.

Frontend
React, TypeScript, Vite, Recharts, Lucide React.

Infrastructure
Docker, Docker Compose.

Testing
Pytest.

5. Project Structure
business-investigator/
|
├── api/
│   ├── main.py
│   └── schemas.py
├── dashboard/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── data/
│   ├── raw/
│   ├── processed/
│   ├── sample/
│   └── uploads/
├── evaluation/
│   └── results/
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
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .dockerignore
├── .env
├── requirements.txt
├── forecast_evaluation.py
├── run_anomaly_evaluation.py
└── README.md
6. Prerequisites
Install:

Python 3.12+

Node.js

npm

Git

Docker Desktop

PostgreSQL (for database integration)

Verify:

python --version
node --version
npm --version
docker --version
docker compose version
7. Installation
Step 1 — Clone
git clone <YOUR_REPOSITORY_URL>
cd business-investigator
Step 2 — Create Python Environment
python -m venv .venv
.venv\Scripts\activate
Step 3 — Install Backend Dependencies
pip install -r requirements.txt
Step 4 — Install Frontend Dependencies
cd dashboard
npm install
cd ..
8. Environment Variables
Create .env in the project root:

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.7-flash
The Gemini key is required for AI-generated investigation explanations.

Never commit a real API key to GitHub.

9. Dataset Setup
The project was developed and evaluated using the UCI Online Retail II transactional dataset.

Expected columns:

Invoice
StockCode
Description
Quantity
InvoiceDate
Price
Customer ID
Country
For local processing, place the raw dataset inside:

data/raw/
Example:

data/raw/online_retail_II.xlsx
The application also supports CSV and Excel uploads through the dashboard/API.

10. Data Processing
The cleaning pipeline:

Loads CSV/Excel data

Standardizes data types

Removes exact duplicates

Identifies cancellation transactions

Handles returns

Removes invalid/bad-debt adjustments

Calculates transaction revenue

Saves processed data

Revenue = Quantity × Price
Processed data is stored in:

data/processed/
11. Business KPI Engine
The KPI engine calculates revenue, orders, customers, units sold, AOV, revenue per customer, new/repeat customers, repeat rate, product performance, daily metrics, monthly metrics, and growth.

Evaluated dataset:

KPI	Value
Total Revenue	£20,465,198.39
Orders	45,330
Customers	5,881
Net Units Sold	10,886,592
Average Order Value	£451.47
Repeat Customer Rate	72.35%
12. Anomaly Detection
Statistical Revenue Detection
A 30-day rolling baseline is used:

Z-score =
(Actual Revenue - Rolling Mean)
/
Rolling Standard Deviation
An anomaly is detected when:

|Z-score| >= 3
Severity:

Z-score	Severity
< 2	NORMAL
2 - < 3	MEDIUM
3 - < 4	HIGH
>= 4	CRITICAL
Multivariate Detection
Isolation Forest evaluates:

Revenue
Orders
Customers
AOV
Units Sold
13. Root Cause Investigation
After an anomaly is detected, the investigation engine analyzes:

Product contribution

Customer contribution

Country contribution

Time contribution

Root-cause ranking

Dimension intersections

Example intersection:

Customer + Product + Country + Hour
This helps identify concentrated business events instead of looking at dimensions independently.

14. Statistical Validation
The investigation pipeline calculates:

Baseline mean

Anomaly revenue

Standard deviation

t-statistic

p-value

Statistical significance

This provides an additional validation layer before the final explanation.

15. Revenue Forecasting
Revenue forecasting uses an XGBoost Regressor.

Target:

next_7_days_revenue
Features:

day_of_week
day_of_month
month
year
revenue_lag_1
revenue_lag_7
revenue_lag_14
revenue_rolling_7
revenue_rolling_30
orders
customers
aov
repeat_customer_rate
A chronological train/test split is used.

Current evaluation:

Metric	Result
Train Rows	561
Test Rows	141
MAE	£34,951.32
RMSE	£44,070.47
MAPE	14.05%
16. SHAP Explainability
SHAP explains which forecasting features have the strongest influence on model predictions, providing model-level interpretability instead of treating the forecast as a black box.

17. Generative AI Explanation
The AI layer follows:

Anomaly
   ↓
Root Cause Analysis
   ↓
Statistical Validation
   ↓
Evidence
   ↓
Gemini
   ↓
Business Explanation
Gemini generates a business-readable explanation containing the event, main contributors, evidence, caveats, and suggested actions.

The LLM is used for explanation, not as the primary source of analytical truth.

18. Run the Backend
From the project root:

uvicorn api.main:app --reload --port 8000
Backend:

http://localhost:8000
Health:

http://localhost:8000/health
Swagger:

http://localhost:8000/docs
Keep this terminal running.

19. Run the Frontend
Open a second terminal:

cd dashboard
npm run dev
Dashboard:

http://localhost:5173
Make sure the backend is running first.

20. Recommended Dashboard Workflow
Open Overview and review KPIs.

Select a dataset.

Open Analytics and inspect revenue/product trends.

Open Anomalies and filter by severity.

Select an anomaly and start an investigation.

Review root causes, contributions, intersections, and evidence.

Review the Gemini explanation.

Export the investigation report as PDF.

Open Forecast and review the 7-day forecast, prediction history, evaluation metrics, and SHAP importance.

21. API Endpoints
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
Interactive documentation:

http://localhost:8000/docs
22. Evaluation
Root Cause Evaluation
Controlled synthetic revenue injections tested country, product, and customer root causes.

Metric	Result
Top-1 Accuracy	100%
Top-3 Accuracy	100%
Result:

evaluation/results/controlled_root_cause_evaluation_v4.json
Anomaly Detection Evaluation
A controlled synthetic anomaly was injected.

Metric	Result
Dates Evaluated	604
Target Detected	Yes
Precision	6.25%
Recall	100%
False Positive Rate	2.49%
Result:

evaluation/anomaly_detection_evaluation.json
The precision result is reported transparently because naturally occurring anomalies were also present during the evaluation period.

Forecast Evaluation
MAE  = £34,951.32
RMSE = £44,070.47
MAPE = 14.05%
Result:

evaluation/results/forecast_evaluation.json
23. Run Automated Tests
From the project root:

pytest -q
Current status:

27 passed
0 failed
The suite covers statistical validation, anomaly detection, root-cause investigation, XGBoost forecasting, SHAP explainability, API functionality, and the investigation pipeline.

Gemini-dependent investigation tests mock the external API call so tests do not depend on live Gemini availability.

24. Docker Setup
Build
docker compose build
Start
docker compose up -d
Check
docker compose ps
Logs
docker compose logs -f backend
Stop
docker compose down
Backend:

http://localhost:8000
Health:

http://localhost:8000/health
Processed and uploaded datasets are mounted from the host machine.

25. PostgreSQL
PostgreSQL is used for structured business data storage.

Main tables include:

customers
products
transactions
daily_metrics
The database layer is kept separate from analytics, machine learning, investigation, API, and frontend components.

26. Troubleshooting
Backend import error
python -c "import api.main; print('API IMPORT OK')"
Then:

uvicorn api.main:app --reload --port 8000
Frontend dependency error
cd dashboard
npm install
npm run dev
Port 8000 already in use
uvicorn api.main:app --reload --port 8001
Then update the frontend API URL.

Docker backend not running
docker compose ps
docker compose logs backend
Gemini error
Check:

GEMINI_API_KEY
GEMINI_MODEL
in .env.

27. Development Principles
Evidence First
Analytical evidence is generated before AI explanation.

Deterministic Core
KPIs, anomaly scores, contribution analysis, statistical tests, and model predictions are generated by dedicated analytical components.

Explainability
SHAP is used to explain forecasting model behavior.

Separation of Concerns
Data
 ↓
Analytics
 ↓
Machine Learning
 ↓
Investigation
 ↓
Evidence
 ↓
AI Explanation
 ↓
API
 ↓
Frontend
Evaluation Driven
Important intelligence components are tested using automated tests and controlled scenarios.

28. Current Project Status
Data Ingestion             ✓
Data Cleaning              ✓
PostgreSQL Integration     ✓
KPI Engine                 ✓
Anomaly Detection          ✓
Root Cause Analysis        ✓
Statistical Validation     ✓
XGBoost Forecasting        ✓
SHAP Explainability        ✓
Evidence Layer             ✓
Gemini Explanation         ✓
FastAPI Backend            ✓
React Dashboard            ✓
Dataset Management         ✓
PDF Reports                ✓
Docker                     ✓
Automated Testing          ✓
Evaluation                 ✓
Documentation              ✓
Current automated test status:

27 passed
0 failed
29. Future Enhancements
User authentication

Multi-user workspaces

Persistent project management

Advanced AI investigation agents

Background investigation jobs

Cloud deployment

Production PostgreSQL deployment

Model monitoring

Automated data-quality monitoring

Additional business datasets

Domain-specific anomaly detectors

30. Author
Yash Rathi

Computer Science & Engineering
Anand International College of Engineering, Jaipur
Rajasthan Technical University, Kota
Academic Session: 2026–2027

31. License
This project is developed for academic and educational purposes.

