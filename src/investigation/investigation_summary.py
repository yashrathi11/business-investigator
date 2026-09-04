import pandas as pd


def build_investigation_summary(
    anomaly_row: pd.Series,
    product_contribution: pd.DataFrame,
    customer_contribution: pd.DataFrame,
    country_contribution: pd.DataFrame,
    time_contribution: pd.DataFrame,
    intersection: pd.DataFrame
) -> dict:
    """
    Build a structured investigation summary
    from anomaly and contribution evidence.
    """

    summary = {
        "anomaly_date": str(anomaly_row["InvoiceDate"]),
        "actual_revenue": float(anomaly_row["revenue"]),
        "expected_revenue": float(anomaly_row["rolling_mean_30"]),
        "z_score": float(anomaly_row["z_score"]),
        "severity": str(anomaly_row["severity"]),
        "revenue_deviation": float(
            anomaly_row["revenue_deviation"]
        ),
        "revenue_deviation_pct": float(
            anomaly_row["revenue_deviation_pct"]
        ),
        "top_product": None,
        "top_customer": None,
        "top_country": None,
        "top_hour": None,
        "intersection": None
    }

    if not product_contribution.empty:
        row = product_contribution.iloc[0]
        summary["top_product"] = {
            "stock_code": str(row["StockCode"]),
            "description": str(row["Description"]),
            "revenue": float(row["revenue"]),
            "contribution_pct": float(row["revenue_share_pct"])
        }

    if not customer_contribution.empty:
        row = customer_contribution.iloc[0]
        summary["top_customer"] = {
            "customer_id": float(row["Customer ID"]),
            "revenue": float(row["revenue"]),
            "contribution_pct": float(row["revenue_share_pct"])
        }

    if not country_contribution.empty:
        row = country_contribution.iloc[0]
        summary["top_country"] = {
            "country": str(row["Country"]),
            "revenue": float(row["revenue"]),
            "contribution_pct": float(row["revenue_share_pct"])
        }

    if not time_contribution.empty:
        row = time_contribution.iloc[0]
        summary["top_hour"] = {
            "hour": int(row["hour"]),
            "revenue": float(row["revenue"]),
            "contribution_pct": float(row["revenue_share_pct"])
        }

    if not intersection.empty:
        row = intersection.iloc[0]
        summary["intersection"] = {
            "revenue": float(row["revenue"]),
            "units_sold": int(row["units_sold"]),
            "orders": int(row["orders"]),
            "transaction_rows": int(row["transaction_rows"])
        }

    return summary