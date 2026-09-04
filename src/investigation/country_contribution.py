import pandas as pd


def calculate_country_contribution(
    transactions: pd.DataFrame,
    anomaly_date,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Calculate country-level revenue contribution
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
                "Country",
                "revenue",
                "units_sold",
                "orders",
                "revenue_share_pct"
            ]
        )

    country_summary = (
        day_data
        .groupby("Country", dropna=False)
        .agg(
            revenue=("Revenue", "sum"),
            units_sold=("Quantity", "sum"),
            orders=("Invoice", "nunique")
        )
        .reset_index()
    )

    total_revenue = country_summary["revenue"].sum()

    if total_revenue != 0:
        country_summary["revenue_share_pct"] = (
            country_summary["revenue"] /
            total_revenue *
            100
        )
    else:
        country_summary["revenue_share_pct"] = 0.0

    return (
        country_summary
        .sort_values("revenue", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )