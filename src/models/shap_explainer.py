import pandas as pd
import shap


def calculate_shap_values(model, X):
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    return explainer, shap_values


def calculate_feature_importance(shap_values, feature_names):
    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": abs(shap_values).mean(axis=0),
        }
    )

    importance = (
        importance
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    return importance


def explain_forecast(model, forecasting_data):
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

    explainer, shap_values = calculate_shap_values(
        model,
        X
    )

    importance = calculate_feature_importance(
        shap_values,
        features
    )

    return {
        "explainer": explainer,
        "shap_values": shap_values,
        "feature_importance": importance,
        "features": features,
        "X": X,
    }


def plot_shap_summary(shap_values, X):
    shap.summary_plot(
        shap_values,
        X,
        show=True
    )