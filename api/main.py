import math
import json
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO

from src.models.revenue_forecaster import (
    prepare_forecasting_features,
    train_revenue_model,
    evaluate_revenue_model,
)

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from xgboost import XGBRegressor
import shap


from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from api.schemas import (
    HealthResponse,
    InvestigationResponse,
)

from src.ingestion.upload_service import (
    create_dataset_id,
    process_uploaded_file,
)

from src.investigation.investigation_engine import (
    investigate_anomaly,
)

from src.analytics.kpi_engine import (
    calculate_daily_metrics,
    calculate_monthly_metrics,
)

from src.analytics.anomaly_detector import (
    calculate_revenue_baseline,
    detect_revenue_anomalies,
    assign_anomaly_severity,
    calculate_revenue_impact,
)


app = FastAPI(
    title="AI Business Investigator API",
    description="Evidence-grounded business anomaly investigation API",
    version="1.0.0",
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://business-investigator.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
)


UPLOAD_DIR = Path("data/uploads")
PROCESSED_DIR = Path("data/processed")


def _read_processed_dataset(path: Path, usecols=None):
    """
    Memory-efficient loader for processed transaction datasets.
    """

    dtype = {
        "StockCode": "category",
        "Country": "category",
    }

    return pd.read_csv(
        path,
        usecols=usecols,
        dtype=dtype,
        parse_dates=["InvoiceDate"],
    )

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# DATASET REGISTRY
# ============================================================
# Keeps uploaded datasets discoverable by the dashboard.
# The processed CSV remains the source of truth for analytics.

DATASET_REGISTRY_FILE = PROCESSED_DIR / "datasets.json"


def _load_dataset_registry():
    if not DATASET_REGISTRY_FILE.exists():
        return []

    try:
        data = json.loads(DATASET_REGISTRY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_dataset_registry(datasets):
    DATASET_REGISTRY_FILE.write_text(
        json.dumps(
            datasets,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _upsert_dataset_metadata(metadata):
    datasets = _load_dataset_registry()

    datasets = [
        item
        for item in datasets
        if item.get("dataset_id") != metadata.get("dataset_id")
    ]

    datasets.insert(0, metadata)

    _save_dataset_registry(datasets)

    return metadata


def _discover_processed_datasets():
    """
    Discover already-processed datasets that were created before
    the registry existed. This keeps the current project dataset
    visible without requiring a re-upload.
    """
    datasets = _load_dataset_registry()
    known_ids = {
        str(item.get("dataset_id"))
        for item in datasets
        if item.get("dataset_id")
    }

    changed = False

    for processed_file in sorted(
        PROCESSED_DIR.glob("*_clean.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        dataset_id = processed_file.name[:-len("_clean.csv")]

        if (
            len(dataset_id) != 32
            or not all(
                character in "0123456789abcdef"
                for character in dataset_id.lower()
            )
            or dataset_id in known_ids
        ):
            continue

        try:
            stat = processed_file.stat()

            datasets.append(
                {
                    "dataset_id": dataset_id,
                    "filename": "Existing processed dataset",
                    "input_rows": None,
                    "output_rows": None,
                    "total_revenue": None,
                    "created_at": datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    ).isoformat(),
                    "source": "existing",
                }
            )

            known_ids.add(dataset_id)
            changed = True

        except OSError:
            continue

    if changed:
        _save_dataset_registry(datasets)

    return datasets


# ============================================================
# JSON SANITIZATION
# ============================================================

def sanitize_for_json(value):
    """
    Convert Pandas/NumPy values and non-finite floats
    into JSON-safe Python values.
    """

    if isinstance(value, dict):
        return {
            str(key): sanitize_for_json(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            sanitize_for_json(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            sanitize_for_json(item)
            for item in value
        ]

    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().isoformat()

    if hasattr(value, "item"):
        return sanitize_for_json(value.item())

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

    return value


# ============================================================
# DATASET ID VALIDATION
# ============================================================

def validate_dataset_id(dataset_id: str):
    """
    Validate UUID-hex dataset IDs generated by create_dataset_id().
    """

    if (
        len(dataset_id) != 32
        or not all(
            character in "0123456789abcdef"
            for character in dataset_id.lower()
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid dataset_id.",
        )


def get_processed_dataset_path(dataset_id: str):
    """
    Return processed dataset path after validating
    that the dataset exists.
    """

    validate_dataset_id(dataset_id)

    processed_file = (
        PROCESSED_DIR
        / f"{dataset_id}_clean.csv"
    )

    if not processed_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {dataset_id}",
        )

    return processed_file


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/health",
    response_model=HealthResponse,
)
def health_check():

    return {
        "status": "healthy",
        "service": "AI Business Investigator API",
    }


# ============================================================
# UPLOAD DATASET
# ============================================================

@app.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...)
):
    try:

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file provided.",
            )

        extension = Path(
            file.filename
        ).suffix.lower()

        allowed_extensions = {
            ".csv",
            ".xlsx",
            ".xls",
        }

        if extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported file type. "
                    "Allowed formats: CSV, XLSX, XLS."
                ),
            )

        dataset_id = create_dataset_id()

        upload_path = (
            UPLOAD_DIR
            / f"{dataset_id}{extension}"
        )

        # Save upload in chunks
        with upload_path.open("wb") as buffer:

            while chunk := await file.read(
                1024 * 1024
            ):
                buffer.write(chunk)

        output_path = (
            PROCESSED_DIR
            / f"{dataset_id}_clean.csv"
        )

        result = process_uploaded_file(
            str(upload_path),
            str(output_path),
        )

        dataset_metadata = {
            "dataset_id": dataset_id,
            "filename": file.filename,
            "input_rows": int(result["input_rows"]),
            "output_rows": int(result["output_rows"]),
            "total_revenue": float(result["total_revenue"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "upload",
        }

        _upsert_dataset_metadata(dataset_metadata)

        return sanitize_for_json({
            "status": "success",
            "dataset": dataset_metadata,
            "dataset_id": dataset_id,
            "filename": file.filename,
            "input_rows": result["input_rows"],
            "output_rows": result["output_rows"],
            "total_revenue": result["total_revenue"],
            "processed_file": result["output_path"],
        })

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(exc)}",
        )


# ============================================================
# DATASETS
# ============================================================

@app.get("/datasets")
def list_datasets():
    """
    Return all datasets known to the API.

    New uploads are stored in datasets.json. Previously processed
    *_clean.csv files are discovered automatically.
    """
    try:
        datasets = _discover_processed_datasets()

        # Most recent first.
        datasets.sort(
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )

        return sanitize_for_json(
            {
                "status": "success",
                "count": len(datasets),
                "datasets": datasets,
            }
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list datasets: {str(exc)}",
        )


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    """
    Return metadata for one dataset.
    """
    validate_dataset_id(dataset_id)

    datasets = _discover_processed_datasets()

    for dataset in datasets:
        if dataset.get("dataset_id") == dataset_id:
            return sanitize_for_json(
                {
                    "status": "success",
                    "dataset": dataset,
                }
            )

    # The file may exist even if metadata is unavailable.
    processed_file = get_processed_dataset_path(dataset_id)

    try:
        stat = processed_file.stat()
        fallback = {
            "dataset_id": dataset_id,
            "filename": "Processed dataset",
            "input_rows": None,
            "output_rows": None,
            "total_revenue": None,
            "created_at": datetime.fromtimestamp(
                stat.st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "source": "existing",
        }

        _upsert_dataset_metadata(fallback)

        return sanitize_for_json(
            {
                "status": "success",
                "dataset": fallback,
            }
        )

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read dataset metadata: {str(exc)}",
        )


# ============================================================
# ANOMALIES
# ============================================================

@app.get("/anomalies/{dataset_id}")
def get_anomalies(dataset_id: str):

    try:

        processed_file = get_processed_dataset_path(
            dataset_id
        )

        # ----------------------------------------------------
        # Load processed transactions
        # ----------------------------------------------------

        df = _read_processed_dataset(
            processed_file,
            usecols=[
                "Invoice",
                "InvoiceDate",
                "Revenue",
                "Quantity",
                "Customer ID",
            ],
        )

        # ----------------------------------------------------
        # Daily metrics
        # ----------------------------------------------------

        daily_metrics = calculate_daily_metrics(
            df
        )

        # ----------------------------------------------------
        # Revenue baseline
        # ----------------------------------------------------

        baseline = calculate_revenue_baseline(
            daily_metrics
        )

        # ----------------------------------------------------
        # Statistical anomalies
        # ----------------------------------------------------

        anomalies = detect_revenue_anomalies(
            baseline
        )

        # ----------------------------------------------------
        # Severity
        # ----------------------------------------------------

        anomalies = assign_anomaly_severity(
            anomalies
        )

        # ----------------------------------------------------
        # Revenue impact
        # ----------------------------------------------------

        anomalies = calculate_revenue_impact(
            anomalies
        )

        # ----------------------------------------------------
        # Only actual statistical anomalies
        # ----------------------------------------------------

        anomalies = anomalies[
            anomalies["is_anomaly"] == True
        ].copy()

        # ----------------------------------------------------
        # Convert to JSON records
        # ----------------------------------------------------

        records = anomalies.to_dict(
            orient="records"
        )

        response = {
            "status": "success",
            "dataset_id": dataset_id,
            "anomaly_count": len(records),
            "anomalies": records,
        }

        return sanitize_for_json(
            response
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to calculate anomalies: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# DATASET SUMMARY
# ============================================================

@app.get("/summary/{dataset_id}")
def get_dataset_summary(dataset_id: str):

    try:

        processed_file = get_processed_dataset_path(
            dataset_id
        )

        # ----------------------------------------------------
        # Load processed transactions
        # ----------------------------------------------------

        df = _read_processed_dataset(
            processed_file,
            usecols=[
                "Invoice",
                "InvoiceDate",
                "Revenue",
                "Quantity",
                "Customer ID",
            ],
        )

        # ----------------------------------------------------
        # Overall KPIs
        # ----------------------------------------------------

        total_revenue = float(
            df["Revenue"].sum()
        )

        total_orders = int(
            df["Invoice"].nunique()
        )

        total_customers = int(
            df["Customer ID"].dropna().nunique()
        )

        total_units_sold = int(
            df["Quantity"].sum()
        )

        average_order_value = (
            total_revenue / total_orders
            if total_orders > 0
            else 0.0
        )

        average_revenue_per_customer = (
            total_revenue / total_customers
            if total_customers > 0
            else 0.0
        )

        # ----------------------------------------------------
        # Daily metrics
        # ----------------------------------------------------

        daily_metrics = calculate_daily_metrics(
            df
        )

        # ----------------------------------------------------
        # Monthly metrics
        # ----------------------------------------------------

        monthly_metrics = calculate_monthly_metrics(
            df
        )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        response = {
            "status": "success",
            "dataset_id": dataset_id,

            "summary": {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "total_customers": total_customers,
                "total_units_sold": total_units_sold,
                "average_order_value": average_order_value,
                "average_revenue_per_customer": (
                    average_revenue_per_customer
                ),
            },

            "daily_metrics": daily_metrics.to_dict(
                orient="records"
            ),

            "monthly_metrics": monthly_metrics.to_dict(
                orient="records"
            ),
        }

        return sanitize_for_json(
            response
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to calculate dataset summary: "
                f"{str(exc)}"
            ),
        )



@app.get("/analytics/{dataset_id}")
def get_analytics(dataset_id: str):
    """
    Return live analytics for the processed dataset.
    This endpoint powers the Analytics page instead of demo/static values.
    """
    try:
        processed_file = get_processed_dataset_path(dataset_id)

        df = _read_processed_dataset(
            processed_file,
            usecols=[
                "Invoice",
                "InvoiceDate",
                "Revenue",
                "Quantity",
                "Customer ID",
                "Description",
            ],
        )

        df = df.dropna(subset=["InvoiceDate"])

        total_revenue = float(df["Revenue"].sum())
        total_orders = int(df["Invoice"].nunique())
        total_customers = int(df["Customer ID"].dropna().nunique())

        aov = total_revenue / total_orders if total_orders else 0.0
        revenue_per_customer = (
            total_revenue / total_customers
            if total_customers
            else 0.0
        )

        # Repeat customer rate: customers with >1 distinct invoice.
        customer_orders = (
            df.dropna(subset=["Customer ID"])
            .groupby("Customer ID")["Invoice"]
            .nunique()
        )
        repeat_rate = (
            float((customer_orders > 1).mean() * 100)
            if len(customer_orders)
            else 0.0
        )

        # Daily revenue + 30-day expected baseline.
        daily = (
            df.groupby(df["InvoiceDate"].dt.normalize(), as_index=False)["Revenue"]
            .sum()
            .rename(columns={"InvoiceDate": "date", "Revenue": "actual"})
            .sort_values("date")
        )
        daily["expected"] = (
            daily["actual"]
            .rolling(30, min_periods=7)
            .mean()
            .shift(1)
            .fillna(daily["actual"].expanding().mean().shift(1))
            .fillna(daily["actual"])
        )

        daily = daily.tail(90).copy()
        daily["date"] = daily["date"].dt.strftime("%d %b")

        # Monthly revenue.
        monthly = (
            df.groupby(df["InvoiceDate"].dt.to_period("M"))["Revenue"]
            .sum()
            .reset_index()
            .sort_values("InvoiceDate")
        )
        monthly["month"] = monthly["InvoiceDate"].dt.strftime("%b %Y")
        monthly["revenue"] = monthly["Revenue"].astype(float)
        monthly = monthly[["month", "revenue"]].tail(18)

        # Top products.
        product_revenue = (
            df.assign(
                Description=df["Description"].fillna("Unknown product")
            )
            .groupby("Description")["Revenue"]
            .sum()
            .nlargest(5)
        )

        top = product_revenue

        top_products = [
            {
                "product": str(product),
                "revenue": float(revenue),
                "share": float((revenue / total_revenue) * 100)
                if total_revenue
                else 0.0,
            }
            for product, revenue in top.items()
        ]

        return {
            "dataset_id": dataset_id,
            "kpis": {
                "average_order_value": aov,
                "revenue_per_customer": revenue_per_customer,
                "repeat_customer_rate": repeat_rate,
                "units_sold": int(df["Quantity"].sum()),
            },
            "daily_revenue": [
                {
                    "date": str(row["date"]),
                    "actual": float(row["actual"]),
                    "expected": float(row["expected"]),
                }
                for _, row in daily.iterrows()
            ],
            "monthly_revenue": [
                {
                    "month": str(row["month"]),
                    "revenue": float(row["revenue"]),
                }
                for _, row in monthly.iterrows()
            ],
            "top_products": top_products,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Analytics calculation failed: {exc}",
        ) from exc


@app.get("/forecast/{dataset_id}")
def forecast_dataset(dataset_id: str):
    """
    Return live XGBoost forecast, evaluation metrics,
    historical test predictions and SHAP feature importance.
    """
    validate_dataset_id(dataset_id)
    dataset_path = get_processed_dataset_path(dataset_id)

    df = _read_processed_dataset(dataset_path)
    daily_metrics = calculate_daily_metrics(df)

    forecasting_data = prepare_forecasting_features(
        daily_metrics=daily_metrics,
        transactions=df,
    )

    if len(forecasting_data) < 20:
        raise HTTPException(
            status_code=400,
            detail="Not enough historical data for forecasting.",
        )

    features = [
        "day_of_week",
        "day_of_month",
        "month",
        "year",
        "revenue_lag_1",
        "revenue_lag_7",
        "revenue_lag_14",
        "revenue_rolling_7",
        "revenue_rolling_30",
        "orders",
        "customers",
        "aov",
        "repeat_customer_rate",
    ]

    evaluation_model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
    )

    evaluation = evaluate_revenue_model(
        evaluation_model,
        forecasting_data,
    )

    split_index = int(len(forecasting_data) * 0.8)
    train_data = forecasting_data.iloc[:split_index]
    test_data = forecasting_data.iloc[split_index:]

    evaluation_model.fit(
        train_data[features],
        train_data["next_7_days_revenue"],
    )

    test_predictions = evaluation_model.predict(test_data[features])

    prediction_history = [
        {
            "date": str(row.InvoiceDate.date()),
            "actual": float(row.next_7_days_revenue),
            "predicted": float(prediction),
        }
        for row, prediction in zip(
            test_data.itertuples(index=False),
            test_predictions,
        )
    ][-60:]

    final_model = train_revenue_model(forecasting_data)
    latest_row = forecasting_data.iloc[[-1]]

    next_7_day_forecast = final_model.predict(
        latest_row[features],
    )[0]

    shap_importance = []

    try:
        sample = test_data[features].tail(100)
        if sample.empty:
            sample = forecasting_data[features].tail(100)

        explainer = shap.TreeExplainer(final_model)
        shap_values = explainer.shap_values(sample)

        importance_values = (
            pd.DataFrame(
                {
                    "feature": features,
                    "importance": abs(shap_values).mean(axis=0),
                }
            )
            .sort_values("importance", ascending=False)
            .head(10)
        )

        shap_importance = [
            {
                "feature": str(row.feature),
                "importance": float(row.importance),
            }
            for row in importance_values.itertuples(index=False)
        ]
    except Exception:
        # SHAP is an explanatory layer; forecasting remains available
        # if the optional explanation dependency has an environment issue.
        shap_importance = []

    return sanitize_for_json(
        {
            "status": "success",
            "dataset_id": dataset_id,
            "model": {
                "name": "XGBRegressor",
                "target": "next_7_days_revenue",
                "features": features,
            },
            "evaluation": {
                "train_rows": evaluation["train_rows"],
                "test_rows": evaluation["test_rows"],
                "mae": evaluation["mae"],
                "rmse": evaluation["rmse"],
                "mape": evaluation["mape"],
            },
            "forecast": {
                "based_on_date": str(
                    latest_row["InvoiceDate"].iloc[0].date()
                ),
                "next_7_days_revenue": float(next_7_day_forecast),
            },
            "prediction_history": prediction_history,
            "shap_importance": shap_importance,
        }
    )


# ============================================================
# INVESTIGATION
# ============================================================

@app.get(
    "/investigate/{dataset_id}/{anomaly_date}",
    response_model=InvestigationResponse,
)
def investigate(
    dataset_id: str,
    anomaly_date: str,
):

    try:

        processed_file = get_processed_dataset_path(
            dataset_id
        )

        # ----------------------------------------------------
        # Run complete investigation engine
        # ----------------------------------------------------

        result = investigate_anomaly(
            anomaly_date,
            data_path=str(processed_file),
        )

        # ----------------------------------------------------
        # Evidence DataFrame → records
        # ----------------------------------------------------

        evidence = result["evidence"]

        if hasattr(evidence, "to_dict"):

            evidence = evidence.to_dict(
                orient="records"
            )

        # ----------------------------------------------------
        # API response
        # ----------------------------------------------------

        response = {
            "status": "success",
            "anomaly_date": anomaly_date,
            "report": result["report"],
            "summary": result["summary"],
            "evidence": evidence,
            "explanation": result["explanation"],
        }

        return sanitize_for_json(
            response
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Investigation failed: "
                f"{str(exc)}"
            ),
        )

# ============================================================
# PDF INVESTIGATION REPORT
# ============================================================

def _report_lines(value, prefix=""):
    """Flatten nested investigation output into readable PDF lines."""
    lines = []

    if isinstance(value, dict):
        for key, item in value.items():
            label = str(key).replace("_", " ").title()
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{label}:")
                lines.extend(_report_lines(item, prefix + "  "))
            else:
                lines.append(f"{prefix}{label}: {item}")

    elif isinstance(value, list):
        for index, item in enumerate(value[:50], start=1):
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}Item {index}:")
                lines.extend(_report_lines(item, prefix + "  "))
            else:
                lines.append(f"{prefix}- {item}")

    else:
        lines.append(f"{prefix}{value}")

    return lines


@app.get("/report/{dataset_id}/{anomaly_date}")
def export_investigation_report(
    dataset_id: str,
    anomaly_date: str,
):
    """
    Run the real investigation engine and export its evidence,
    summary and Gemini explanation as a PDF.
    """

    try:
        processed_file = get_processed_dataset_path(dataset_id)

        result = investigate_anomaly(
            anomaly_date,
            data_path=str(processed_file),
        )

        buffer = BytesIO()

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=14,
        )

        heading_style = ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=12,
            spaceAfter=7,
        )

        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontSize=9,
            leading=13,
            spaceAfter=6,
        )

        small_style = ParagraphStyle(
            "ReportSmall",
            parent=styles["BodyText"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#667085"),
        )

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=42,
            leftMargin=42,
            topMargin=42,
            bottomMargin=42,
            title=f"Business Investigator Report - {anomaly_date}",
            author="Business Investigator",
        )

        story = []

        story.append(
            Paragraph(
                "Business Investigator",
                title_style,
            )
        )

        story.append(
            Paragraph(
                f"Investigation Report · {anomaly_date}",
                heading_style,
            )
        )

        story.append(
            Paragraph(
                "Evidence-backed business anomaly investigation generated "
                "from the uploaded dataset.",
                body_style,
            )
        )

        story.append(
            Paragraph(
                "AI Explanation",
                heading_style,
            )
        )

        explanation = str(
            result.get(
                "explanation",
                "No AI explanation returned.",
            )
        )

        for paragraph in explanation.split("\n"):
            if paragraph.strip():
                story.append(
                    Paragraph(
                        paragraph.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                        body_style,
                    )
                )

        story.append(
            Paragraph(
                "Investigation Summary",
                heading_style,
            )
        )

        summary_lines = _report_lines(
            result.get("summary", {})
        )

        if summary_lines:
            table_data = [["Finding", "Value"]]

            for line in summary_lines[:40]:
                clean = line.strip()
                if ":" in clean:
                    key, value = clean.split(":", 1)
                    table_data.append([key, value.strip()])
                else:
                    table_data.append(["", clean])

            table = Table(
                table_data,
                colWidths=[150, 350],
                repeatRows=1,
            )

            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff1f2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#d92d38")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("LEADING", (0, 0), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )

            story.append(table)

        story.append(
            Paragraph(
                "Evidence",
                heading_style,
            )
        )

        evidence = result.get("evidence", [])
        evidence_lines = _report_lines(evidence)

        for line in evidence_lines[:80]:
            safe_line = (
                str(line)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            story.append(
                Paragraph(
                    safe_line,
                    small_style,
                )
            )

        story.append(Spacer(1, 12))

        story.append(
            Paragraph(
                "Methodology note: statistical and machine-learning outputs "
                "are computed by the investigation pipeline. The language "
                "model is used to explain the supplied evidence and should "
                "not be treated as independent proof of fraud, authenticity "
                "or business intent.",
                small_style,
            )
        )

        doc.build(story)

        buffer.seek(0)

        filename = (
            f"business-investigator-{anomaly_date}.pdf"
        )

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                )
            },
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(exc)}",
        )
