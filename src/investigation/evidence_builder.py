import pandas as pd


def build_evidence(
    investigation_summary: dict,
    product_contribution: pd.DataFrame,
    customer_contribution: pd.DataFrame,
    country_contribution: pd.DataFrame,
    time_contribution: pd.DataFrame,
    intersection: dict
):
    """
    Build structured, evidence-backed findings
    from the investigation results.
    """

    evidence = []

    # ---------------------------------------------------------
    # Anomaly evidence
    # ---------------------------------------------------------

    evidence.append({
        "evidence_type": "anomaly",
        "dimension": "revenue",
        "finding": (
            f"Revenue was £{investigation_summary['actual_revenue']:,.2f}, "
            f"against an expected £{investigation_summary['expected_revenue']:,.2f}."
        ),
        "impact": (
            f"{investigation_summary['revenue_deviation_pct']:.2f}% "
            "above expected revenue."
        ),
        "strength": "high"
    })

    # ---------------------------------------------------------
    # Product evidence
    # ---------------------------------------------------------

    if not product_contribution.empty:
        top_product = product_contribution.iloc[0]

        evidence.append({
            "evidence_type": "contribution",
            "dimension": "product",
            "identifier": str(top_product["StockCode"]),
            "finding": (
                f"{top_product['Description']} generated "
                f"£{top_product['revenue']:,.2f}."
            ),
            "impact": (
                f"{top_product['revenue_share_pct']:.2f}% "
                "of anomaly-day revenue."
            ),
            "strength": "high"
        })

    # ---------------------------------------------------------
    # Customer evidence
    # ---------------------------------------------------------

    if not customer_contribution.empty:
        top_customer = customer_contribution.iloc[0]

        evidence.append({
            "evidence_type": "contribution",
            "dimension": "customer",
            "identifier": str(top_customer["Customer ID"]),
            "finding": (
                f"Customer {top_customer['Customer ID']} generated "
                f"£{top_customer['revenue']:,.2f}."
            ),
            "impact": (
                f"{top_customer['revenue_share_pct']:.2f}% "
                "of identified-customer revenue."
            ),
            "strength": "high"
        })

    # ---------------------------------------------------------
    # Country evidence
    # ---------------------------------------------------------

    if not country_contribution.empty:
        top_country = country_contribution.iloc[0]

        evidence.append({
            "evidence_type": "contribution",
            "dimension": "country",
            "identifier": str(top_country["Country"]),
            "finding": (
                f"{top_country['Country']} generated "
                f"£{top_country['revenue']:,.2f}."
            ),
            "impact": (
                f"{top_country['revenue_share_pct']:.2f}% "
                "of anomaly-day revenue."
            ),
            "strength": "high"
        })

    # ---------------------------------------------------------
    # Time evidence
    # ---------------------------------------------------------

    if not time_contribution.empty:
        top_hour = time_contribution.iloc[0]

        evidence.append({
            "evidence_type": "contribution",
            "dimension": "time",
            "identifier": str(top_hour["hour"]),
            "finding": (
                f"The {int(top_hour['hour']):02d}:00 hour generated "
                f"£{top_hour['revenue']:,.2f}."
            ),
            "impact": (
                f"{top_hour['revenue_share_pct']:.2f}% "
                "of anomaly-day revenue."
            ),
            "strength": "high"
        })

     # ---------------------------------------------------------
    # Intersection evidence
    # ---------------------------------------------------------

    if intersection is not None:

        intersection_revenue = float(
            intersection["revenue"].sum()
        )

        if intersection_revenue > 0:
            evidence.append({
                "evidence_type": "intersection",
                "dimension": "multi_dimension",
                "finding": (
                    "Multiple investigation dimensions "
                    "co-occurred in the same transaction subset."
                ),
                "impact": (
                    f"Intersection revenue: "
                    f"£{intersection_revenue:,.2f}."
                ),
                "strength": "critical"
            })

    return pd.DataFrame(evidence)