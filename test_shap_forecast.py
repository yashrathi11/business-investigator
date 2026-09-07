import pandas as pd

from src.analytics.kpi_engine import calculate_daily_metrics
from src.models.revenue_forecaster import (
    prepare_forecasting_features,
    train_revenue_model,
)
from src.models.shap_explainer import explain_forecast


df = pd.read_csv(
    "data/processed/clean_transactions.csv"
)

daily = calculate_daily_metrics(df)

data = prepare_forecasting_features(
    daily,
    df
)

model = train_revenue_model(data)

result = explain_forecast(
    model,
    data
)

print("Feature count:", len(result["features"]))

print("\nFeatures:")
for feature in result["features"]:
    print("-", feature)

print("\nSHAP Feature Importance:")
print(
    result["feature_importance"]
    .to_string(index=False)
)

print("\nSHAP values shape:")
print(result["shap_values"].shape)