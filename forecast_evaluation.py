from pathlib import Path
import json

import pandas as pd

from src.analytics.kpi_engine import calculate_daily_metrics
from src.models.revenue_forecaster import (
    prepare_forecasting_features,
    train_revenue_model,
    evaluate_revenue_model,
)


BASE_FILE = Path("data/processed/clean_transactions.csv")
RESULT_DIR = Path("evaluation/results")
RESULT_DIR.mkdir(parents=True, exist_ok=True)

RESULT_FILE = RESULT_DIR / "forecast_evaluation.json"


def main():
    print("=" * 70)
    print("FORECAST MODEL EVALUATION")
    print("=" * 70)

    # ------------------------------------------------------------
    # Load cleaned transaction data
    # ------------------------------------------------------------
    print("\nLoading transaction data...")

    df = pd.read_csv(BASE_FILE)

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"]
    )

    print(f"Rows loaded: {len(df):,}")

    # ------------------------------------------------------------
    # Build daily metrics
    # ------------------------------------------------------------
    print("\nBuilding daily metrics...")

    daily_metrics = calculate_daily_metrics(df)

    print(
        f"Daily metric rows: "
        f"{len(daily_metrics):,}"
    )

    # ------------------------------------------------------------
    # Prepare forecasting features
    # ------------------------------------------------------------
    print("\nPreparing forecasting features...")

    forecasting_data = prepare_forecasting_features(
        daily_metrics,
        transactions=df,
    )

    print(
        f"Forecasting rows: "
        f"{len(forecasting_data):,}"
    )

    print(
        f"Forecasting columns: "
        f"{len(forecasting_data.columns)}"
    )

    # ------------------------------------------------------------
    # Train XGBoost model
    # ------------------------------------------------------------
    print("\nTraining XGBoost model...")

    model = train_revenue_model(
        forecasting_data
    )

    print(
        f"Model type: "
        f"{type(model).__name__}"
    )

    # ------------------------------------------------------------
    # Evaluate model
    # ------------------------------------------------------------
    print("\nEvaluating model...")

    evaluation = evaluate_revenue_model(
        model,
        forecasting_data,
    )

    print("\nRaw evaluation output:")
    print(evaluation)

    # ------------------------------------------------------------
    # Convert evaluation result into JSON-safe format
    # ------------------------------------------------------------
    def convert_value(value):
       if isinstance(value, pd.Timestamp):
        return value.isoformat()

       if isinstance(value, pd.Series):
        return value.tolist()

       if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")

       if hasattr(value, "tolist"):
        return value.tolist()

       if hasattr(value, "item"):
        return value.item()

        return value

    if isinstance(evaluation, dict):
        metrics = {
            str(key): convert_value(value)
            for key, value in evaluation.items()
        }
    else:
        metrics = {
            "evaluation_result": convert_value(
                evaluation
            )
        }

    # ------------------------------------------------------------
    # Extract common metrics if available
    # ------------------------------------------------------------
    def find_metric(possible_names):
        for name in possible_names:
            if name in metrics:
                return metrics[name]

            # Case-insensitive lookup
            for key in metrics:
                if str(key).lower() == name.lower():
                    return metrics[key]

        return None

    mae = find_metric(
        ["mae", "MAE"]
    )

    rmse = find_metric(
        ["rmse", "RMSE"]
    )

    mape = find_metric(
        ["mape", "MAPE"]
    )

    # ------------------------------------------------------------
    # Forecast dataset information
    # ------------------------------------------------------------
    date_column = None

    for candidate in [
        "InvoiceDate",
        "date",
        "Date",
    ]:
        if candidate in forecasting_data.columns:
            date_column = candidate
            break

    date_start = None
    date_end = None

    if date_column is not None:
        dates = pd.to_datetime(
            forecasting_data[date_column]
        )

        date_start = str(
            dates.min().date()
        )

        date_end = str(
            dates.max().date()
        )

    # ------------------------------------------------------------
    # Save final evaluation artifact
    # ------------------------------------------------------------
    result = {
        "evaluation": "xgboost_revenue_forecast",
        "model": {
            "name": type(model).__name__,
            "target": "next_7_days_revenue",
        },
        "dataset": {
            "source": str(BASE_FILE),
            "transaction_rows": int(len(df)),
            "daily_rows": int(len(daily_metrics)),
            "forecasting_rows": int(
                len(forecasting_data)
            ),
            "date_start": date_start,
            "date_end": date_end,
        },
        "metrics": metrics,
    }

    RESULT_FILE.write_text(
        json.dumps(
            result,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------
    print("\n" + "=" * 70)
    print("FORECAST EVALUATION SUMMARY")
    print("=" * 70)

    print(
        f"Model      : {type(model).__name__}"
    )

    print(
        "Target     : next_7_days_revenue"
    )

    if mae is not None:
        print(
            f"MAE        : £{float(mae):,.2f}"
        )

    if rmse is not None:
        print(
            f"RMSE       : £{float(rmse):,.2f}"
        )

    if mape is not None:
        print(
            f"MAPE       : {float(mape):.2f}%"
        )

    print(
        f"\nResults saved to:\n"
        f"{RESULT_FILE}"
    )

    print("\n" + "=" * 70)
    print("FORECAST EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()