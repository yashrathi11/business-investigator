import pandas as pd
import numpy as np
from xgboost import XGBRegressor


def prepare_forecasting_features(daily_metrics, transactions=None):
    df = daily_metrics.copy()

    # ---------------------------------------------------------
    # 1. Date preparation
    # ---------------------------------------------------------
    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    ).dt.normalize()

    df = df.dropna(subset=["InvoiceDate"])
    df = df.sort_values("InvoiceDate")

    # ---------------------------------------------------------
    # 2. Create continuous daily calendar
    # ---------------------------------------------------------
    date_range = pd.date_range(
        start=df["InvoiceDate"].min(),
        end=df["InvoiceDate"].max(),
        freq="D"
    )

    df = (
        df.set_index("InvoiceDate")
        .reindex(date_range)
        .rename_axis("InvoiceDate")
        .reset_index()
    )

    # Business metrics: missing calendar days = zero activity
    for column in ["revenue", "orders", "customers", "units_sold"]:
        if column in df.columns:
            df[column] = df[column].fillna(0)

    # AOV = revenue / orders
    df["aov"] = np.where(
        df["orders"] > 0,
        df["revenue"] / df["orders"],
        0
    )

    # ---------------------------------------------------------
    # 3. Repeat customer rate
    # ---------------------------------------------------------
    df["repeat_customer_rate"] = 0.0

    if transactions is not None:
        tx = transactions.copy()

        tx["InvoiceDate"] = pd.to_datetime(
            tx["InvoiceDate"],
            errors="coerce"
        ).dt.normalize()

        tx = tx.dropna(subset=["InvoiceDate"])

        customer_orders = (
            tx.dropna(subset=["Customer ID"])
            .groupby(["InvoiceDate", "Customer ID"])["Invoice"]
            .nunique()
            .reset_index(name="order_count")
        )

        daily_customer_metrics = (
            customer_orders
            .groupby("InvoiceDate")
            .agg(
                total_customers=("Customer ID", "nunique"),
                repeat_customers=(
                    "order_count",
                    lambda x: (x > 1).sum()
                )
            )
            .reset_index()
        )

        daily_customer_metrics["repeat_customer_rate"] = np.where(
            daily_customer_metrics["total_customers"] > 0,
            (
                daily_customer_metrics["repeat_customers"]
                / daily_customer_metrics["total_customers"]
            ) * 100,
            0
        )

        df = df.merge(
            daily_customer_metrics[
                [
                    "InvoiceDate",
                    "repeat_customer_rate"
                ]
            ],
            on="InvoiceDate",
            how="left",
            suffixes=("", "_tx")
        )

        df["repeat_customer_rate"] = (
            df["repeat_customer_rate_tx"]
            .fillna(df["repeat_customer_rate"])
            .fillna(0)
        )

        df = df.drop(
            columns=["repeat_customer_rate_tx"],
            errors="ignore"
        )

    # ---------------------------------------------------------
    # 4. Calendar features
    # ---------------------------------------------------------
    df["day_of_week"] = df["InvoiceDate"].dt.dayofweek
    df["day_of_month"] = df["InvoiceDate"].dt.day
    df["month"] = df["InvoiceDate"].dt.month
    df["year"] = df["InvoiceDate"].dt.year

    # ---------------------------------------------------------
    # 5. Historical revenue features
    # ---------------------------------------------------------
    df["revenue_lag_1"] = df["revenue"].shift(1)
    df["revenue_lag_7"] = df["revenue"].shift(7)
    df["revenue_lag_14"] = df["revenue"].shift(14)

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

    # ---------------------------------------------------------
    # 6. Next 7 days revenue target
    # ---------------------------------------------------------
    future_revenues = pd.concat(
        [
            df["revenue"].shift(-i)
            for i in range(1, 8)
        ],
        axis=1
    )

    df["next_7_days_revenue"] = future_revenues.sum(axis=1)

    # Only rows with complete 7-day future window
    df.loc[
        future_revenues.isna().any(axis=1),
        "next_7_days_revenue"
    ] = np.nan

    # ---------------------------------------------------------
    # 7. Remove rows without enough history/future
    # ---------------------------------------------------------
    df = df.dropna(
        subset=[
            "revenue_lag_1",
            "revenue_lag_7",
            "revenue_lag_14",
            "revenue_rolling_7",
            "revenue_rolling_30",
            "next_7_days_revenue"
        ]
    )

    return df


def train_revenue_model(forecasting_data):
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

    X = forecasting_data[features]
    y = forecasting_data["next_7_days_revenue"]

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

    return model


def evaluate_revenue_model(model, forecasting_data):
    import numpy as np
    from sklearn.metrics import mean_absolute_error, mean_squared_error

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

    split_index = int(len(forecasting_data) * 0.8)

    train_data = forecasting_data.iloc[:split_index]
    test_data = forecasting_data.iloc[split_index:]

    X_train = train_data[features]
    y_train = train_data["next_7_days_revenue"]

    X_test = test_data[features]
    y_test = test_data["next_7_days_revenue"]

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)

    rmse = np.sqrt(
        mean_squared_error(y_test, predictions)
    )

    non_zero = y_test != 0

    if non_zero.any():
        mape = (
            np.mean(
                np.abs(
                    (y_test[non_zero] - predictions[non_zero])
                    / y_test[non_zero]
                )
            )
            * 100
        )
    else:
        mape = np.nan

    return {
        "train_rows": len(train_data),
        "test_rows": len(test_data),
        "mae": float(mae),
        "rmse": float(rmse),
        "mape": float(mape),
        "predictions": predictions,
        "actual": y_test.to_numpy(),
        "test_dates": test_data["InvoiceDate"].to_numpy(),
    }