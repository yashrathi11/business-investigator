from pathlib import Path
import json

import pandas as pd

from src.analytics.anomaly_detector import (
    calculate_revenue_baseline,
    detect_revenue_anomalies,
    assign_anomaly_severity,
    calculate_revenue_impact,
)

from src.investigation.product_contribution import (
    calculate_product_contribution,
)

from src.investigation.customer_contribution import (
    calculate_customer_contribution,
)

from src.investigation.country_contribution import (
    calculate_country_contribution,
)

from src.investigation.time_contribution import (
    calculate_time_contribution,
)

from src.investigation.root_cause_ranker import (
    rank_root_causes,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "clean_transactions.csv"
)

RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# CONFIGURATION
# ============================================================

# Controlled evaluation scenarios.
#
# Each scenario has:
#   - anomaly date
#   - expected root-cause dimension
#
# The real dataset is used as the evaluation source.
# We evaluate whether the investigation engine identifies
# the strongest known contributor for each anomaly date.

SCENARIOS = [
    {
        "name": "known_major_anomaly",
        "date": "2011-12-09",
        "expected_dimension": "product",
    },
    {
        "name": "known_secondary_anomaly",
        "date": "2010-09-27",
        "expected_dimension": "country",
    },
]


# ============================================================
# HELPERS
# ============================================================

def load_transactions() -> pd.DataFrame:
    """Load and prepare the cleaned transaction dataset."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce",
    )

    df["Revenue"] = pd.to_numeric(
        df["Revenue"],
        errors="coerce",
    )

    df["Quantity"] = pd.to_numeric(
        df["Quantity"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["InvoiceDate"]
    ).copy()

    return df


def calculate_anomalies(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Run the existing revenue anomaly pipeline."""

    daily = (
        df.groupby(
            df["InvoiceDate"].dt.normalize()
        )
        .agg(
            revenue=("Revenue", "sum"),
            orders=("Invoice", "nunique"),
            customers=("Customer ID", "nunique"),
            units_sold=("Quantity", "sum"),
        )
        .reset_index()
    )

    daily["aov"] = (
        daily["revenue"]
        / daily["orders"].replace(0, pd.NA)
    )

    daily["aov"] = daily["aov"].fillna(0)

    baseline = calculate_revenue_baseline(
        daily
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

    return anomalies


def calculate_contributions(
    df: pd.DataFrame,
    anomaly_date: str,
):
    """Calculate all existing contribution dimensions."""

    date = pd.to_datetime(
        anomaly_date
    ).normalize()

    product = calculate_product_contribution(
        df,
        date,
    )

    customer = calculate_customer_contribution(
        df,
        date,
    )

    country = calculate_country_contribution(
        df,
        date,
    )

    time = calculate_time_contribution(
        df,
        date,
    )

    return (
        product,
        customer,
        country,
        time,
    )


def evaluate_root_cause(
    product: pd.DataFrame,
    customer: pd.DataFrame,
    country: pd.DataFrame,
    time: pd.DataFrame,
    expected_dimension: str,
):
    """Evaluate Top-1 and Top-3 root-cause dimension accuracy."""

    ranked = rank_root_causes(
        product,
        customer,
        country,
        time,
        top_n=10,
    )

    if ranked.empty:
        return {
            "top_1_correct": False,
            "top_3_correct": False,
            "predicted_top_1": None,
            "top_3_dimensions": [],
            "ranked_causes": [],
        }

    dimensions = (
        ranked["dimension"]
        .astype(str)
        .tolist()
    )

    predicted_top_1 = dimensions[0]

    top_3_dimensions = dimensions[:3]

    return {
        "top_1_correct": (
            predicted_top_1
            == expected_dimension
        ),
        "top_3_correct": (
            expected_dimension
            in top_3_dimensions
        ),
        "predicted_top_1": predicted_top_1,
        "top_3_dimensions": top_3_dimensions,
        "ranked_causes": (
            ranked
            .head(10)
            .to_dict(orient="records")
        ),
    }


def evaluate_anomaly_detection(
    anomalies: pd.DataFrame,
    scenario_dates: list[str],
):
    """
    Evaluate anomaly detection against known scenario dates.

    Positive class:
        scenario date

    Negative class:
        all other evaluated dates

    This is a controlled scenario evaluation rather than
    a full ground-truth benchmark.
    """

    anomalies = anomalies.copy()

    anomalies["InvoiceDate"] = pd.to_datetime(
        anomalies["InvoiceDate"],
        errors="coerce",
    ).dt.normalize()

    scenario_dates_normalized = {
        pd.to_datetime(date).normalize()
        for date in scenario_dates
    }

    detected_dates = set(
        anomalies.loc[
            anomalies["is_anomaly"] == True,
            "InvoiceDate",
        ].dropna()
    )

    true_positives = len(
        scenario_dates_normalized
        & detected_dates
    )

    false_negatives = len(
        scenario_dates_normalized
        - detected_dates
    )

    # For FPR, the evaluation universe is all
    # dates represented by the anomaly detector.
    all_dates = set(
        anomalies["InvoiceDate"].dropna()
    )

    negative_dates = (
        all_dates
        - scenario_dates_normalized
    )

    false_positives = len(
        detected_dates
        & negative_dates
    )

    true_negatives = len(
        negative_dates
        - detected_dates
    )

    precision = (
        true_positives
        / (true_positives + false_positives)
        if (true_positives + false_positives)
        else 0.0
    )

    recall = (
        true_positives
        / (true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 0.0
    )

    false_positive_rate = (
        false_positives
        / (false_positives + true_negatives)
        if (false_positives + true_negatives)
        else 0.0
    )

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "false_positive_rate": false_positive_rate,
        "evaluated_positive_dates": [
            str(x.date())
            for x in sorted(
                scenario_dates_normalized
            )
        ],
        "detected_anomaly_dates": [
            str(x.date())
            for x in sorted(
                detected_dates
            )
        ],
    }


# ============================================================
# MAIN EVALUATION
# ============================================================

def main():

    print("=" * 70)
    print("AI BUSINESS INVESTIGATOR - DAY 8 EVALUATION")
    print("=" * 70)

    print()
    print("Loading dataset...")

    df = load_transactions()

    print(
        f"Dataset rows: {len(df):,}"
    )

    print()
    print("Running anomaly detection...")

    anomalies = calculate_anomalies(
        df
    )

    print(
        "Anomaly rows evaluated:",
        len(anomalies),
    )

    scenario_dates = [
        scenario["date"]
        for scenario in SCENARIOS
    ]

    # --------------------------------------------------------
    # Anomaly evaluation
    # --------------------------------------------------------

    anomaly_metrics = evaluate_anomaly_detection(
        anomalies,
        scenario_dates,
    )

    # --------------------------------------------------------
    # Root-cause evaluation
    # --------------------------------------------------------

    root_cause_results = []

    for scenario in SCENARIOS:

        name = scenario["name"]
        date = scenario["date"]
        expected = scenario[
            "expected_dimension"
        ]

        print()
        print("-" * 70)
        print(
            f"Scenario: {name}"
        )
        print(
            f"Date: {date}"
        )
        print(
            f"Expected dimension: {expected}"
        )

        (
            product,
            customer,
            country,
            time,
        ) = calculate_contributions(
            df,
            date,
        )

        result = evaluate_root_cause(
            product,
            customer,
            country,
            time,
            expected,
        )

        result_record = {
            "scenario": name,
            "date": date,
            "expected_dimension": expected,
            **result,
        }

        root_cause_results.append(
            result_record
        )

        print(
            "Predicted Top-1:",
            result["predicted_top_1"],
        )

        print(
            "Top-3:",
            result["top_3_dimensions"],
        )

        print(
            "Top-1 correct:",
            result["top_1_correct"],
        )

        print(
            "Top-3 correct:",
            result["top_3_correct"],
        )

    # --------------------------------------------------------
    # Aggregate root-cause metrics
    # --------------------------------------------------------

    total_scenarios = len(
        root_cause_results
    )

    top_1_correct = sum(
        r["top_1_correct"]
        for r in root_cause_results
    )

    top_3_correct = sum(
        r["top_3_correct"]
        for r in root_cause_results
    )

    top_1_accuracy = (
        top_1_correct
        / total_scenarios
        if total_scenarios
        else 0.0
    )

    top_3_accuracy = (
        top_3_correct
        / total_scenarios
        if total_scenarios
        else 0.0
    )

    root_cause_metrics = {
        "total_scenarios": total_scenarios,
        "top_1_correct": top_1_correct,
        "top_3_correct": top_3_correct,
        "top_1_accuracy": top_1_accuracy,
        "top_3_accuracy": top_3_accuracy,
    }

    # --------------------------------------------------------
    # Final evaluation object
    # --------------------------------------------------------

    evaluation = {
        "project": "AI Business Investigator",
        "evaluation_type": (
            "controlled scenario evaluation"
        ),
        "dataset": str(DATA_PATH),
        "root_cause_metrics": (
            root_cause_metrics
        ),
        "root_cause_results": (
            root_cause_results
        ),
        "anomaly_metrics": (
            anomaly_metrics
        ),
    }

    output_path = (
        RESULTS_DIR
        / "evaluation_summary.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            evaluation,
            f,
            indent=2,
            default=str,
        )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    print()
    print(
        f"Root Cause Top-1 Accuracy : "
        f"{top_1_accuracy * 100:.2f}%"
    )

    print(
        f"Root Cause Top-3 Accuracy : "
        f"{top_3_accuracy * 100:.2f}%"
    )

    print(
        f"Anomaly Precision         : "
        f"{anomaly_metrics['precision'] * 100:.2f}%"
    )

    print(
        f"Anomaly Recall            : "
        f"{anomaly_metrics['recall'] * 100:.2f}%"
    )

    print(
        f"Anomaly False Positive Rate: "
        f"{anomaly_metrics['false_positive_rate'] * 100:.2f}%"
    )

    print()
    print(
        f"Results saved to:"
    )
    print(output_path)

    print()
    print("=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()