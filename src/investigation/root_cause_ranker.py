import pandas as pd


def rank_root_causes(
    product_contribution: pd.DataFrame,
    customer_contribution: pd.DataFrame,
    country_contribution: pd.DataFrame,
    time_contribution: pd.DataFrame,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Rank potential root causes across product, customer,
    country, and time dimensions using revenue contribution.
    """

    causes = []

    for _, row in product_contribution.head(top_n).iterrows():
        causes.append({
            "dimension": "product",
            "cause": row["Description"],
            "revenue": row["revenue"],
            "contribution_pct": row["revenue_share_pct"],
            "orders": row["orders"],
            "units": row["units_sold"]
        })

    for _, row in customer_contribution.head(top_n).iterrows():
        causes.append({
            "dimension": "customer",
            "cause": str(row["Customer ID"]),
            "revenue": row["revenue"],
            "contribution_pct": row["revenue_share_pct"],
            "orders": row["orders"],
            "units": row["units_sold"]
        })

    for _, row in country_contribution.head(top_n).iterrows():
        causes.append({
            "dimension": "country",
            "cause": row["Country"],
            "revenue": row["revenue"],
            "contribution_pct": row["revenue_share_pct"],
            "orders": row["orders"],
            "units": row["units_sold"]
        })

    for _, row in time_contribution.head(top_n).iterrows():
        causes.append({
            "dimension": "hour",
            "cause": f"{int(row['hour']):02d}:00",
            "revenue": row["revenue"],
            "contribution_pct": row["revenue_share_pct"],
            "orders": row["orders"],
            "units": row["units_sold"]
        })

    if not causes:
        return pd.DataFrame(
            columns=[
                "dimension",
                "cause",
                "revenue",
                "contribution_pct",
                "orders",
                "units"
            ]
        )

    result = pd.DataFrame(causes)

    return (
        result
        .sort_values(
            ["contribution_pct", "revenue"],
            ascending=False
        )
        .head(top_n)
        .reset_index(drop=True)
    )