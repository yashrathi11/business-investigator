import pandas as pd


def calculate_product_contribution(
    transactions: pd.DataFrame,
    anomaly_date,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Calculate product-level revenue contribution
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

    if day_data.empty:
        return pd.DataFrame(
            columns=[
                "StockCode",
                "Description",
                "revenue",
                "units_sold",
                "orders",
                "revenue_share_pct"
            ]
        )

    product_summary = (
        day_data
        .groupby(
            ["StockCode", "Description"],
            dropna=False
        )
        .agg(
            revenue=("Revenue", "sum"),
            units_sold=("Quantity", "sum"),
            orders=("Invoice", "nunique")
        )
        .reset_index()
    )

    total_revenue = product_summary["revenue"].sum()

    if total_revenue != 0:
        product_summary["revenue_share_pct"] = (
            product_summary["revenue"]
            / total_revenue
        ) * 100
    else:
        product_summary["revenue_share_pct"] = 0.0

    product_summary = (
        product_summary
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(top_n)
        .reset_index(drop=True)
    )

    return product_summary