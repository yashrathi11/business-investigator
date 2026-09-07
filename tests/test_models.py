import sys

sys.path.insert(0, "src")

import numpy as np
import pandas as pd

from analytics.statistical_tests import compare_anomaly_period
from models.revenue_forecaster import (
    prepare_forecasting_features,
    train_revenue_model,
)
from models.shap_explainer import (
    calculate_shap_values,
    calculate_feature_importance,
)


FEATURE_COLUMNS = [
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


def create_sample_daily_metrics():
    dates = pd.date_range(
        start="2020-01-01",
        periods=80,
        freq="D"
    )

    revenue = np.linspace(1000, 3000, 80)

    return pd.DataFrame({
        "InvoiceDate": dates,
        "revenue": revenue,
        "orders": np.arange(20, 100),
        "customers": np.arange(10, 90),
        "units_sold": np.arange(100, 180),
        "aov": revenue / np.arange(20, 100),
    })


def test_statistical_validation():
    dates = pd.date_range(
        start="2020-01-01",
        periods=31,
        freq="D"
    )

    revenue = [1000] * 30 + [10000]

    transactions = pd.DataFrame({
        "InvoiceDate": dates,
        "Revenue": revenue
    })

    result = compare_anomaly_period(
        transactions,
        "2020-01-31"
    )

    assert result["is_significant"] is True
    assert result["anomaly_revenue"] == 10000
    assert result["p_value"] < 0.05


def test_xgboost_forecasting():
    daily_metrics = create_sample_daily_metrics()

    forecasting_data = prepare_forecasting_features(
        daily_metrics
    )

    model = train_revenue_model(
        forecasting_data
    )

    predictions = model.predict(
        forecasting_data[FEATURE_COLUMNS]
    )

    assert len(predictions) == len(forecasting_data)
    assert len(FEATURE_COLUMNS) == 13
    assert np.isfinite(predictions).all()


def test_shap_explainability():
    daily_metrics = create_sample_daily_metrics()

    forecasting_data = prepare_forecasting_features(
        daily_metrics
    )

    model = train_revenue_model(
        forecasting_data
    )

    X = forecasting_data[FEATURE_COLUMNS]

    explainer, shap_values = calculate_shap_values(
        model,
        X
    )

    importance = calculate_feature_importance(
        shap_values,
        FEATURE_COLUMNS
    )

    assert shap_values.shape == (
        len(X),
        len(FEATURE_COLUMNS)
    )

    assert len(importance) == len(FEATURE_COLUMNS)

    assert importance["importance"].notna().all()
