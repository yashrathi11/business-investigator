import pandas as pd
import numpy as np

from xgboost import XGBRegressor


def prepare_forecasting_features(daily_metrics: pd.DataFrame):
    """
    Create time-series features for revenue forecasting.
    """

    df = daily_metrics.copy()

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    df = df.sort_values("InvoiceDate").reset_index(drop=True)

    # Calendar features
    df["day_of_week"] = df["InvoiceDate"].dt.dayofweek
    df["day_of_month"] = df["InvoiceDate"].dt.day
    df["month"] = df["InvoiceDate"].dt.month
    df["year"] = df["InvoiceDate"].dt.year

    # Lag features
    df["revenue_lag_1"] = df["revenue"].shift(1)
    df["revenue_lag_7"] = df["revenue"].shift(7)
    df["revenue_lag_30"] = df["revenue"].shift(30)

    # Rolling features
    df["revenue_rolling_7"] = (
        df["revenue"]
        .shift(1)
        .rolling(7)
        .mean()
    )

    df["revenue_rolling_30"] = (
        df["revenue"]
        .shift(1)
        .rolling(30)
        .mean()
    )

    # Remove rows created by lag/rolling operations
    df = df.dropna().reset_index(drop=True)

    return df


def train_revenue_model(
    forecasting_data: pd.DataFrame
):
    """
    Train XGBoost revenue forecasting model.
    """

    feature_columns = [
        "day_of_week",
        "day_of_month",
        "month",
        "year",
        "revenue_lag_1",
        "revenue_lag_7",
        "revenue_lag_30",
        "revenue_rolling_7",
        "revenue_rolling_30",
    ]

    X = forecasting_data[feature_columns]
    y = forecasting_data["revenue"]

    model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42
    )

    model.fit(X, y)

    return model, feature_columns