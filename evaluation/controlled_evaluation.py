from pathlib import Path
import json

import pandas as pd

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


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "clean_transactions.csv"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# CONFIGURATION
# ============================================================

EVALUATION_DATE = pd.Timestamp(
    "2011-09-26"
)

SYNTHETIC_REVENUE = 100_000.0

# Spread synthetic transactions across many hours.
# This prevents "hour" from becoming an artificial
# root cause.

SYNTHETIC_HOURS = [
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
]

SCENARIOS = [
    "country",
    "product",
    "customer",
]


# ============================================================
# LOAD DATA
# ============================================================

def load_transactions():

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(
        DATA_PATH
    )

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


# ============================================================
# BASE DAY
# ============================================================

def get_base_day(df):

    day = df[
        df["InvoiceDate"].dt.normalize()
        == EVALUATION_DATE
    ].copy()

    if day.empty:
        raise ValueError(
            f"No transactions found for "
            f"{EVALUATION_DATE.date()}"
        )

    return day


# ============================================================
# TARGET SELECTION
# ============================================================

def select_targets(day_df):

    # --------------------------------------------------------
    # Country
    # --------------------------------------------------------

    countries = (
        day_df.groupby("Country")
        .agg(
            revenue=("Revenue", "sum"),
            rows=("Revenue", "size"),
        )
        .sort_values(
            "revenue",
            ascending=False,
        )
    )

    country = countries.index[0]

    # --------------------------------------------------------
    # Product
    # --------------------------------------------------------

    products = (
        day_df.groupby(
            [
                "StockCode",
                "Description",
            ],
            dropna=False,
        )
        .agg(
            revenue=("Revenue", "sum"),
            rows=("Revenue", "size"),
        )
        .query("rows >= 2")
        .sort_values(
            "revenue",
            ascending=False,
        )
    )

    if products.empty:
        raise ValueError(
            "No suitable product found."
        )

    product_stock = (
        products.index[0][0]
    )

    product_description = (
        products.index[0][1]
    )

    # --------------------------------------------------------
    # Customer
    # --------------------------------------------------------

    customers = (
        day_df.dropna(
            subset=["Customer ID"]
        )
        .groupby("Customer ID")
        .agg(
            revenue=("Revenue", "sum"),
            rows=("Revenue", "size"),
        )
        .query("rows >= 2")
        .sort_values(
            "revenue",
            ascending=False,
        )
    )

    if customers.empty:
        raise ValueError(
            "No suitable customer found."
        )

    customer = customers.index[0]

    return {
        "country": {
            "country": str(
                country
            ),
        },
        "product": {
            "stock_code": str(
                product_stock
            ),
            "description": str(
                product_description
            ),
        },
        "customer": {
            "customer_id": str(
                customer
            ),
        },
    }


# ============================================================
# SYNTHETIC ROW BUILDER
# ============================================================

def build_synthetic_rows(
    dimension,
    target,
):
    """
    Build controlled synthetic transactions.

    Revenue is distributed evenly across many hours,
    preventing hour from becoming a confounding factor.
    """

    rows = []

    revenue_per_row = (
        SYNTHETIC_REVENUE
        / len(SYNTHETIC_HOURS)
    )

    base_invoice = 9_000_000

    for index, hour in enumerate(
        SYNTHETIC_HOURS
    ):

        row = {
            "Invoice": (
                base_invoice
                + index
            ),

            "StockCode": (
                target["stock_code"]
                if dimension == "product"
                else f"CONTROL-{dimension.upper()}"
            ),

            "Description": (
                target["description"]
                if dimension == "product"
                else "Controlled Evaluation Transaction"
            ),

            "Quantity": 1,

            "InvoiceDate": (
                EVALUATION_DATE
                + pd.Timedelta(
                    hours=hour
                )
            ),

            "Price": revenue_per_row,

            "Customer ID": (
                float(
                    target["customer_id"]
                )
                if dimension == "customer"
                else 999999.0
            ),

            "Country": (
                target["country"]
                if dimension == "country"
                else "Controlled Evaluation Country"
            ),

            "Revenue": revenue_per_row,
        }

        rows.append(
            row
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# BUILD SYNTHETIC DATASET
# ============================================================

def build_synthetic_dataset(
    day_df,
    dimension,
    target,
):

    synthetic_rows = (
        build_synthetic_rows(
            dimension,
            target,
        )
    )

    synthetic_df = pd.concat(
        [
            day_df.copy(),
            synthetic_rows,
        ],
        ignore_index=True,
    )

    return synthetic_df


# ============================================================
# CONTRIBUTION ANALYSIS
# ============================================================

def run_analysis(
    df,
    date,
):

    product = calculate_product_contribution(
        df,
        date,
        top_n=10,
    )

    customer = calculate_customer_contribution(
        df,
        date,
        top_n=10,
    )

    country = calculate_country_contribution(
        df,
        date,
        top_n=10,
    )

    time = calculate_time_contribution(
        df,
        date,
        top_n=20,
    )

    ranked = rank_root_causes(
        product,
        customer,
        country,
        time,
        top_n=10,
    )

    return {
        "product": product,
        "customer": customer,
        "country": country,
        "time": time,
        "ranked": ranked,
    }


# ============================================================
# TARGET RANK
# ============================================================

def find_target_rank(
    ranked,
    dimension,
    target,
):

    if ranked.empty:
        return None

    if dimension == "country":

        expected = str(
            target["country"]
        )

    elif dimension == "product":

        expected = str(
            target["description"]
        )

    elif dimension == "customer":

        expected = str(
            target["customer_id"]
        )

    else:
        return None

    for index, row in ranked.iterrows():

        if str(
            row["dimension"]
        ) != dimension:
            continue

        if str(
            row["cause"]
        ) == expected:

            return index + 1

    return None


# ============================================================
# SCENARIO EVALUATION
# ============================================================

def evaluate_scenario(
    day_df,
    dimension,
    target,
):

    synthetic_df = (
        build_synthetic_dataset(
            day_df,
            dimension,
            target,
        )
    )

    analysis = run_analysis(
        synthetic_df,
        EVALUATION_DATE,
    )

    ranked = analysis["ranked"]

    rank = find_target_rank(
        ranked,
        dimension,
        target,
    )

    return {
        "scenario": dimension,

        "expected_dimension": (
            dimension
        ),

        "expected_target": (
            target.get("country")
            or target.get("description")
            or target.get("customer_id")
        ),

        "synthetic_revenue": (
            SYNTHETIC_REVENUE
        ),

        "synthetic_hours": (
            SYNTHETIC_HOURS
        ),

        "target_rank": rank,

        "top_1_correct": (
            rank == 1
        ),

        "top_3_correct": (
            rank is not None
            and rank <= 3
        ),

        "predicted_top_1": (
            str(
                ranked.iloc[0]["dimension"]
            )
            if not ranked.empty
            else None
        ),

        "top_5": (
            ranked.head(5)
            .to_dict(
                orient="records"
            )
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print(
        "AI BUSINESS INVESTIGATOR"
    )
    print(
        "CONTROLLED ROOT-CAUSE EVALUATION V4"
    )
    print("=" * 72)

    print()
    print("Loading dataset...")

    df = load_transactions()

    print(
        f"Rows loaded: {len(df):,}"
    )

    print()
    print(
        "Evaluation date:",
        EVALUATION_DATE.date(),
    )

    day_df = get_base_day(
        df
    )

    print(
        "Base-day rows:",
        len(day_df),
    )

    print(
        "Base-day revenue:",
        f"£{day_df['Revenue'].sum():,.2f}",
    )

    # --------------------------------------------------------
    # Targets
    # --------------------------------------------------------

    targets = select_targets(
        day_df
    )

    print()
    print("Targets selected:")

    print(
        "Country:",
        targets["country"]["country"],
    )

    print(
        "Product:",
        targets["product"]["description"],
    )

    print(
        "Customer:",
        targets["customer"]["customer_id"],
    )

    print()
    print(
        "Synthetic revenue:",
        f"£{SYNTHETIC_REVENUE:,.2f}",
    )

    print(
        "Synthetic hours:",
        ", ".join(
            f"{hour:02d}:00"
            for hour in SYNTHETIC_HOURS
        ),
    )

    # --------------------------------------------------------
    # Scenarios
    # --------------------------------------------------------

    results = []

    for dimension in SCENARIOS:

        print()
        print("-" * 72)

        print(
            "Scenario:",
            dimension,
        )

        result = evaluate_scenario(
            day_df,
            dimension,
            targets[dimension],
        )

        results.append(
            result
        )

        print(
            "Expected:",
            result[
                "expected_dimension"
            ],
        )

        print(
            "Target:",
            result[
                "expected_target"
            ],
        )

        print(
            "Predicted Top-1:",
            result[
                "predicted_top_1"
            ],
        )

        print(
            "Target rank:",
            result[
                "target_rank"
            ],
        )

        print(
            "Top-1 correct:",
            result[
                "top_1_correct"
            ],
        )

        print(
            "Top-3 correct:",
            result[
                "top_3_correct"
            ],
        )

        print(
            "Top-5:"
        )

        for cause in result[
            "top_5"
        ]:

            print(
                "  -",
                cause["dimension"],
                "|",
                cause["cause"],
            )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    total = len(
        results
    )

    top_1_correct = sum(
        result[
            "top_1_correct"
        ]
        for result in results
    )

    top_3_correct = sum(
        result[
            "top_3_correct"
        ]
        for result in results
    )

    top_1_accuracy = (
        top_1_correct
        / total
    )

    top_3_accuracy = (
        top_3_correct
        / total
    )

    metrics = {
        "scenario_count": total,
        "top_1_correct": top_1_correct,
        "top_3_correct": top_3_correct,
        "top_1_accuracy": top_1_accuracy,
        "top_3_accuracy": top_3_accuracy,
    }

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output = {
        "evaluation_type": (
            "controlled synthetic anomaly"
        ),

        "evaluation_version": "v4",

        "dataset": str(
            DATA_PATH
        ),

        "evaluation_date": str(
            EVALUATION_DATE.date()
        ),

        "synthetic_revenue": (
            SYNTHETIC_REVENUE
        ),

        "synthetic_hours": (
            SYNTHETIC_HOURS
        ),

        "metrics": metrics,

        "results": results,
    }

    output_path = (
        RESULTS_DIR
        / "controlled_root_cause_evaluation_v4.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            default=str,
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print(
        "CONTROLLED EVALUATION V4 SUMMARY"
    )
    print("=" * 72)

    print()

    print(
        f"Top-1 Accuracy : "
        f"{top_1_accuracy * 100:.2f}%"
    )

    print(
        f"Top-3 Accuracy : "
        f"{top_3_accuracy * 100:.2f}%"
    )

    print()
    print(
        "Results saved to:"
    )

    print(
        output_path
    )

    print()
    print("=" * 72)
    print(
        "CONTROLLED EVALUATION V4 COMPLETE"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()