import pandas as pd

from src.analytics.kpi_engine import calculate_daily_metrics
from src.models.revenue_forecaster import (
    prepare_forecasting_features,
    train_revenue_model,
    evaluate_revenue_model,
)


df = pd.read_csv(
    "data/processed/clean_transactions.csv"
)

daily = calculate_daily_metrics(df)

data = prepare_forecasting_features(
    daily,
    df
)

model = train_revenue_model(data)

result = evaluate_revenue_model(
    model,
    data
)

print("Train rows:", result["train_rows"])
print("Test rows:", result["test_rows"])

print(
    f"MAE: £{result['mae']:,.2f}"
)

print(
    f"RMSE: £{result['rmse']:,.2f}"
)

print(
    f"MAPE: {result['mape']:.2f}%"
)

print("\nFirst 5 predictions:")

for date, actual, predicted in zip(
    result["test_dates"][:5],
    result["actual"][:5],
    result["predictions"][:5],
):
    print(
        date,
        f"Actual=£{actual:,.2f}",
        f"Predicted=£{predicted:,.2f}"
    )