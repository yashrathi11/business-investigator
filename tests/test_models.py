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

    model, feature_columns = train_revenue_model(
        forecasting_data
    )

    predictions = model.predict(
        forecasting_data[feature_columns]
    )

    assert len(predictions) == len(forecasting_data)
    assert len(feature_columns) == 9
    assert np.isfinite(predictions).all()


def test_shap_explainability():
    daily_metrics = create_sample_daily_metrics()

    forecasting_data = prepare_forecasting_features(
        daily_metrics
    )

    model, feature_columns = train_revenue_model(
        forecasting_data
    )

    X = forecasting_data[feature_columns]

    explainer, shap_values = calculate_shap_values(
        model,
        X
    )

    importance = calculate_feature_importance(
        shap_values,
        feature_columns
    )

    assert shap_values.shape == (
        len(X),
        len(feature_columns)
    )

    assert len(importance) == len(feature_columns)

    assert importance["importance"].notna().all()