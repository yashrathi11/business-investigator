import pandas as pd


def analyze_anomaly_intersection(
    transactions: pd.DataFrame,
    anomaly_date,
    customer_id=None,
    stock_code=None,
    country=None,
    hour=None
) -> pd.DataFrame:
    """
    Analyze the intersection of multiple dimensions
    for a specific anomaly date.
    """

    df = transactions.copy()

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    anomaly_date = pd.to_datetime(anomaly_date).date()

    filtered = df[
        df["InvoiceDate"].dt.date == anomaly_date
    ].copy()

    if customer_id is not None:
        filtered = filtered[
            filtered["Customer ID"] == customer_id
        ]

    if stock_code is not None:
        filtered = filtered[
            filtered["StockCode"] == stock_code
        ]

    if country is not None:
        filtered = filtered[
            filtered["Country"] == country
        ]

    if hour is not None:
        filtered = filtered[
            filtered["InvoiceDate"].dt.hour == hour
        ]

    if filtered.empty:
        return pd.DataFrame(
            columns=[
                "revenue",
                "units_sold",
                "orders",
                "transaction_rows"
            ]
        )

    result = pd.DataFrame([{
        "revenue": filtered["Revenue"].sum(),
        "units_sold": filtered["Quantity"].sum(),
        "orders": filtered["Invoice"].nunique(),
        "transaction_rows": len(filtered)
    }])

    return result