from fastapi.testclient import TestClient

import api.main as main


client = TestClient(main.app)

DATASET_ID = "18159f6dc06f4f16a4a55bdc7c330235"


def fake_investigation(anomaly_date, data_path=None):
    if anomaly_date == "invalid-date":
        raise ValueError(
            f"No anomaly found for date: {anomaly_date}"
        )

    return {
        "report": {
            "investigation": {
                "anomaly_date": anomaly_date,
                "severity": "CRITICAL",
                "actual_revenue": 200918.98,
                "expected_revenue": 60084.96,
                "revenue_deviation": 140834.02,
                "revenue_deviation_pct": 234.39,
                "z_score": 7.27,
            },
            "root_causes": {},
            "intersection": {},
            "evidence": [],
        },
        "summary": {
            "anomaly_date": anomaly_date,
        },
        "evidence": [],
        "explanation": "Test investigation explanation.",
    }


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "AI Business Investigator API"


def test_summary_endpoint():
    response = client.get(
        f"/summary/{DATASET_ID}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["dataset_id"] == DATASET_ID

    summary = data["summary"]

    assert summary["total_revenue"] > 0
    assert summary["total_orders"] > 0
    assert summary["total_customers"] > 0
    assert summary["total_units_sold"] == 10886592
    assert summary["average_order_value"] > 0
    assert summary["average_revenue_per_customer"] > 0

    assert "daily_metrics" in data
    assert "monthly_metrics" in data


def test_anomalies_endpoint():
    response = client.get(
        f"/anomalies/{DATASET_ID}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["dataset_id"] == DATASET_ID

    assert data["anomaly_count"] > 0
    assert "anomalies" in data

    anomaly_dates = [
        anomaly["InvoiceDate"]
        for anomaly in data["anomalies"]
    ]

    assert "2011-12-09" in anomaly_dates


def test_forecast_endpoint():
    response = client.get(
        f"/forecast/{DATASET_ID}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["dataset_id"] == DATASET_ID

    assert data["model"]["name"] == "XGBRegressor"
    assert data["model"]["target"] == "next_7_days_revenue"

    evaluation = data["evaluation"]

    assert evaluation["train_rows"] > 0
    assert evaluation["test_rows"] > 0
    assert evaluation["mae"] >= 0
    assert evaluation["rmse"] >= 0
    assert evaluation["mape"] >= 0

    forecast = data["forecast"]

    assert "based_on_date" in forecast
    assert forecast["next_7_days_revenue"] >= 0


def test_investigation_endpoint(monkeypatch):
    monkeypatch.setattr(
        main,
        "investigate_anomaly",
        fake_investigation,
    )

    response = client.get(
        f"/investigate/{DATASET_ID}/2011-12-09"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["anomaly_date"] == "2011-12-09"

    assert "report" in data
    assert "summary" in data
    assert "evidence" in data
    assert "explanation" in data

    assert (
        data["report"]["investigation"]["severity"]
        == "CRITICAL"
    )


def test_invalid_investigation(monkeypatch):
    monkeypatch.setattr(
        main,
        "investigate_anomaly",
        fake_investigation,
    )

    response = client.get(
        f"/investigate/{DATASET_ID}/invalid-date"
    )

    assert response.status_code == 404

    data = response.json()

    assert "detail" in data
    assert "No anomaly found" in data["detail"]