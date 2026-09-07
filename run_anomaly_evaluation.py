from pathlib import Path
import json

import pandas as pd

from src.analytics.kpi_engine import calculate_daily_metrics
from src.analytics.anomaly_detector import (
    calculate_revenue_baseline,
    detect_revenue_anomalies,
    assign_anomaly_severity,
    calculate_revenue_impact,
)


BASE_FILE = Path("data/processed/clean_transactions.csv")
EVAL_DIR = Path("evaluation")
EVAL_DIR.mkdir(exist_ok=True)

TEMP_FILE = EVAL_DIR / "anomaly_eval_dataset.csv"
RESULT_FILE = EVAL_DIR / "anomaly_detection_evaluation.json"


def run_detector(data_path: Path) -> pd.DataFrame:
    df = pd.read_csv(data_path)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

    daily = calculate_daily_metrics(df)

    baseline = calculate_revenue_baseline(
        daily,
        window=30,
    )

    anomalies = detect_revenue_anomalies(
        baseline,
        z_threshold=3.0,
    )

    anomalies = assign_anomaly_severity(anomalies)
    anomalies = calculate_revenue_impact(anomalies)

    return anomalies


def calculate_metrics(
    ground_truth_anomalies,
    detected_anomalies,
    normal_dates,
):
    ground_truth_anomalies = set(ground_truth_anomalies)
    detected_anomalies = set(detected_anomalies)
    normal_dates = set(normal_dates)

    true_positive = len(
        ground_truth_anomalies & detected_anomalies
    )

    false_negative = len(
        ground_truth_anomalies - detected_anomalies
    )

    false_positive = len(
        detected_anomalies & normal_dates
    )

    true_negative = len(
        normal_dates - detected_anomalies
    )

    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive) > 0
        else 0.0
    )

    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative) > 0
        else 0.0
    )

    false_positive_rate = (
        false_positive / (false_positive + true_negative)
        if (false_positive + true_negative) > 0
        else 0.0
    )

    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": precision,
        "recall": recall,
        "false_positive_rate": false_positive_rate,
    }


def main():
    print("=" * 70)
    print("ANOMALY DETECTION CONTROLLED EVALUATION")
    print("=" * 70)

    # ------------------------------------------------------------
    # Load original dataset
    # ------------------------------------------------------------
    original = pd.read_csv(BASE_FILE)
    original["InvoiceDate"] = pd.to_datetime(
        original["InvoiceDate"]
    )

    daily = calculate_daily_metrics(original)

    daily = daily.sort_values(
        "InvoiceDate"
    ).reset_index(drop=True)

    # ------------------------------------------------------------
    # Select a historical date with enough baseline history
    # ------------------------------------------------------------
    eligible = daily.iloc[40:-10].copy()

    if eligible.empty:
        raise RuntimeError(
            "Could not find an eligible historical date."
        )

    base_row = eligible.iloc[len(eligible) // 2]

    target_date = pd.Timestamp(
        base_row["InvoiceDate"]
    ).normalize()

    print(
        f"\nSelected base date: {target_date.date()}"
    )

    # ------------------------------------------------------------
    # Original revenue
    # ------------------------------------------------------------
    original_day_mask = (
        original["InvoiceDate"].dt.normalize()
        == target_date
    )

    original_day_revenue = original.loc[
        original_day_mask,
        "Revenue",
    ].sum()

    print(
        f"Original day revenue: "
        f"£{original_day_revenue:,.2f}"
    )

    # ------------------------------------------------------------
    # Controlled synthetic shock
    # ------------------------------------------------------------
    synthetic_revenue = max(
        100000.0,
        abs(original_day_revenue) * 3.0,
    )

    day_rows = original.loc[
        original_day_mask
    ].copy()

    if day_rows.empty:
        raise RuntimeError(
            "Selected date contains no transactions."
        )

    # Spread synthetic revenue across all rows
    # on the selected date.
    per_row_revenue = (
        synthetic_revenue / len(day_rows)
    )

    day_rows["Revenue"] = (
        day_rows["Revenue"]
        + per_row_revenue
    )

    modified = original.copy()

    modified.loc[
        day_rows.index,
        "Revenue",
    ] = day_rows["Revenue"]

    modified.to_csv(
        TEMP_FILE,
        index=False,
    )

    print(
        f"Injected synthetic revenue: "
        f"£{synthetic_revenue:,.2f}"
    )

    # ------------------------------------------------------------
    # Run anomaly detector
    # ------------------------------------------------------------
    anomalies = run_detector(
        TEMP_FILE
    )

    # ------------------------------------------------------------
    # IMPORTANT:
    # Only rows where is_anomaly == True
    # are actual detections.
    # ------------------------------------------------------------
    anomaly_rows = anomalies[
        anomalies["is_anomaly"] == True
    ].copy()

    detected_dates = set(
        pd.to_datetime(
            anomaly_rows["InvoiceDate"]
        )
        .dt.normalize()
        .tolist()
    )

    print(
        f"\nTotal dates evaluated: "
        f"{len(anomalies)}"
    )

    print(
        f"Actual anomalies detected: "
        f"{len(anomaly_rows)}"
    )

    print("\nDetected anomalies:")

    if anomaly_rows.empty:
        print("  NONE")
    else:
        for _, row in anomaly_rows.iterrows():
            print(
                f"  {row['InvoiceDate']} | "
                f"severity={row['severity']} | "
                f"z_score={row['z_score']:.4f}"
            )

    # ------------------------------------------------------------
    # Ground truth
    # ------------------------------------------------------------
    ground_truth_anomaly_dates = {
        target_date
    }

    all_dates = set(
        pd.to_datetime(
            daily["InvoiceDate"]
        )
        .dt.normalize()
        .tolist()
    )

    normal_dates = (
        all_dates
        - ground_truth_anomaly_dates
    )

    # ------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------
    metrics = calculate_metrics(
        ground_truth_anomalies=ground_truth_anomaly_dates,
        detected_anomalies=detected_dates,
        normal_dates=normal_dates,
    )

    target_detected = (
        target_date in detected_dates
    )

    # ------------------------------------------------------------
    # Result JSON
    # ------------------------------------------------------------
    result = {
        "evaluation": "controlled_anomaly_detection",
        "method": {
            "baseline_window": 30,
            "z_threshold": 3.0,
            "synthetic_shock": True,
        },
        "scenario": {
            "target_date": str(
                target_date.date()
            ),
            "original_revenue": float(
                original_day_revenue
            ),
            "synthetic_revenue_injected": float(
                synthetic_revenue
            ),
        },
        "detection": {
            "target_detected": target_detected,
            "detected_anomaly_count": len(
                detected_dates
            ),
            "detected_dates": [
                str(date.date())
                for date in sorted(
                    detected_dates
                )
            ],
        },
        "metrics": {
            "true_positive": metrics[
                "true_positive"
            ],
            "false_positive": metrics[
                "false_positive"
            ],
            "false_negative": metrics[
                "false_negative"
            ],
            "true_negative": metrics[
                "true_negative"
            ],
            "precision": metrics[
                "precision"
            ],
            "recall": metrics[
                "recall"
            ],
            "false_positive_rate": metrics[
                "false_positive_rate"
            ],
        },
    }

    RESULT_FILE.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------
    print("\n" + "=" * 70)
    print("CONTROLLED ANOMALY EVALUATION SUMMARY")
    print("=" * 70)

    print(
        "Target anomaly detected : "
        f"{'YES' if target_detected else 'NO'}"
    )

    print(
        f"Precision               : "
        f"{metrics['precision'] * 100:.2f}%"
    )

    print(
        f"Recall                  : "
        f"{metrics['recall'] * 100:.2f}%"
    )

    print(
        f"False Positive Rate     : "
        f"{metrics['false_positive_rate'] * 100:.2f}%"
    )

    print(
        f"\nResults saved to: "
        f"{RESULT_FILE}"
    )

    # Cleanup
    if TEMP_FILE.exists():
        TEMP_FILE.unlink()

    print("\n" + "=" * 70)
    print("CONTROLLED ANOMALY EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()