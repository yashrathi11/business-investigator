import sys
sys.path.insert(0, "src")

import pandas as pd

from analytics.kpi_engine import calculate_daily_metrics
from analytics.anomaly_detector import (
    calculate_revenue_baseline,
    detect_revenue_anomalies,
    assign_anomaly_severity,
    calculate_revenue_impact,
    detect_multivariate_anomalies,
    combine_anomaly_results,
)


def load_daily_metrics():
    df = pd.read_csv(
        "data/processed/clean_transactions.csv"
    )

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    return calculate_daily_metrics(df)


def test_revenue_baseline():
    daily_metrics = load_daily_metrics()

    baseline = calculate_revenue_baseline(
        daily_metrics
    )

    assert "rolling_mean_30" in baseline.columns
    assert "rolling_std_30" in baseline.columns
    assert "z_score" in baseline.columns


def test_statistical_anomalies():
    daily_metrics = load_daily_metrics()

    baseline = calculate_revenue_baseline(
        daily_metrics
    )

    anomalies = detect_revenue_anomalies(
        baseline
    )

    assert "is_anomaly" in anomalies.columns
    assert anomalies["is_anomaly"].sum() > 0


def test_severity_and_impact():
    daily_metrics = load_daily_metrics()

    baseline = calculate_revenue_baseline(
        daily_metrics
    )

    anomalies = detect_revenue_anomalies(
        baseline
    )

    anomalies = assign_anomaly_severity(
        anomalies
    )

    anomalies = calculate_revenue_impact(
        anomalies
    )

    assert "severity" in anomalies.columns
    assert "revenue_deviation" in anomalies.columns
    assert "revenue_deviation_pct" in anomalies.columns


def test_multivariate_anomalies():
    daily_metrics = load_daily_metrics()

    result = detect_multivariate_anomalies(
        daily_metrics
    )

    assert "is_multivariate_anomaly" in result.columns
    assert "isolation_score" in result.columns
    assert result["is_multivariate_anomaly"].sum() > 0


def test_final_anomaly_combination():
    daily_metrics = load_daily_metrics()

    baseline = calculate_revenue_baseline(
        daily_metrics
    )

    statistical = detect_revenue_anomalies(
        baseline
    )

    statistical = assign_anomaly_severity(
        statistical
    )

    statistical = calculate_revenue_impact(
        statistical
    )

    multivariate = detect_multivariate_anomalies(
        daily_metrics
    )

    final = combine_anomaly_results(
        statistical,
        multivariate
    )

    assert "final_anomaly" in final.columns
    assert final["final_anomaly"].sum() > 0