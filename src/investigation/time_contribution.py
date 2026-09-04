import pandas as pd


def calculate_time_contribution(
    transactions: pd.DataFrame,
    anomaly_date,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Calculate hourly revenue contribution
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
                "hour",
                "revenue",
                "units_sold",
                "orders",
                "revenue_share_pct"
            ]
        )

    day_data["hour"] = day_data["InvoiceDate"].dt.hour

    hourly_summary = (
        day_data
        .groupby("hour")
        .agg(
            revenue=("Revenue", "sum"),
            units_sold=("Quantity", "sum"),
            orders=("Invoice", "nunique")
        )
        .reset_index()
    )

    total_revenue = hourly_summary["revenue"].sum()

    if total_revenue != 0:
        hourly_summary["revenue_share_pct"] = (
            hourly_summary["revenue"] /
            total_revenue *
            100
        )
    else:
        hourly_summary["revenue_share_pct"] = 0.0

    return (
        hourly_summary
        .sort_values("revenue", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )