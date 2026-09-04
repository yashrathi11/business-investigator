import pandas as pd


def calculate_customer_contribution(
    transactions: pd.DataFrame,
    anomaly_date,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Calculate customer-level revenue contribution
    for a specific anomaly date.
    """

    df = transactions.copy()

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    anomaly_date = pd.to_datetime(anomaly_date).date()

    day_data = df[
        df["InvoiceDate"].dt.date == anomaly_date
    ].copy()

    # Ignore transactions without a customer ID
    day_data = day_data[
        day_data["Customer ID"].notna()
    ]

    if day_data.empty:
        return pd.DataFrame(
            columns=[
                "Customer ID",
                "revenue",
                "units_sold",
                "orders",
                "revenue_share_pct"
            ]
        )

    customer_summary = (
        day_data
        .groupby("Customer ID")
        .agg(
            revenue=("Revenue", "sum"),
            units_sold=("Quantity", "sum"),
            orders=("Invoice", "nunique")
        )
        .reset_index()
    )

    total_revenue = customer_summary["revenue"].sum()

    if total_revenue != 0:
        customer_summary["revenue_share_pct"] = (
            customer_summary["revenue"]
            / total_revenue
        ) * 100
    else:
        customer_summary["revenue_share_pct"] = 0.0

    customer_summary = (
        customer_summary
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    return customer_summary