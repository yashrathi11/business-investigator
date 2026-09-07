import pandas as pd

from src.analytics.anomaly_detector import (
    calculate_revenue_baseline,
    detect_revenue_anomalies,
    assign_anomaly_severity,
    calculate_revenue_impact,
)

from src.investigation.product_contribution import calculate_product_contribution
from src.investigation.customer_contribution import calculate_customer_contribution
from src.investigation.country_contribution import calculate_country_contribution
from src.investigation.time_contribution import calculate_time_contribution
from src.investigation.intersection_analysis import analyze_anomaly_intersection
from src.investigation.investigation_summary import build_investigation_summary
from src.investigation.evidence_builder import build_evidence
from src.investigation.evidence_ranker import rank_evidence
from src.investigation.investigation_report import build_investigation_report
from src.investigation.llm_explainer import generate_investigation_explanation


def investigate_anomaly(
    anomaly_date,
    data_path="data/processed/clean_transactions.csv",
):
    """
    Run the complete business investigation pipeline
    for a selected anomaly date.
    """

    # ---------------------------------------------------------
    # 1. Load transactions
    # ---------------------------------------------------------
    df = pd.read_csv(data_path)

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    # ---------------------------------------------------------
    # 2. Build daily metrics
    # ---------------------------------------------------------
    daily = (
        df.groupby(df["InvoiceDate"].dt.normalize())
        .agg(
            revenue=("Revenue", "sum"),
            orders=("Invoice", "nunique"),
            customers=("Customer ID", "nunique"),
            units_sold=("Quantity", "sum"),
        )
        .reset_index()
    )

    daily["aov"] = daily["revenue"] / daily["orders"]

    # ---------------------------------------------------------
    # 3. Detect anomalies
    # ---------------------------------------------------------
    baseline = calculate_revenue_baseline(daily)

    anomalies = detect_revenue_anomalies(baseline)

    anomalies = assign_anomaly_severity(anomalies)

    anomalies = calculate_revenue_impact(anomalies)

    anomaly_date = pd.to_datetime(anomaly_date).normalize()

    matching = anomalies[
      (anomalies["InvoiceDate"] == anomaly_date)
    & (anomalies["is_anomaly"] == True)
    ]

    if matching.empty:
     raise ValueError(
        f"No anomaly found for date: {anomaly_date.date()}"
    )

    anomaly_row = matching.iloc[0]

    # ---------------------------------------------------------
    # 4. Contribution analysis
    # ---------------------------------------------------------
    products = calculate_product_contribution(
        df,
        anomaly_date
    )

    customers = calculate_customer_contribution(
        df,
        anomaly_date
    )

    countries = calculate_country_contribution(
        df,
        anomaly_date
    )

    times = calculate_time_contribution(
        df,
        anomaly_date
    )

    # ---------------------------------------------------------
    # 5. Determine strongest intersection
    # ---------------------------------------------------------
    top_product = (
        products.iloc[0]["StockCode"]
        if not products.empty
        else None
    )

    top_customer = (
        customers.iloc[0]["Customer ID"]
        if not customers.empty
        else None
    )

    top_country = (
        countries.iloc[0]["Country"]
        if not countries.empty
        else None
    )

    top_hour = (
        int(times.iloc[0]["hour"])
        if not times.empty
        else None
    )

    intersection = analyze_anomaly_intersection(
        df,
        anomaly_date,
        customer_id=top_customer,
        stock_code=top_product,
        country=top_country,
        hour=top_hour,
    )

    # ---------------------------------------------------------
    # 6. Investigation summary
    # ---------------------------------------------------------
    summary = build_investigation_summary(
        anomaly_row,
        products,
        customers,
        countries,
        times,
        intersection,
    )

    # ---------------------------------------------------------
    # 7. Build evidence
    # ---------------------------------------------------------
    evidence = build_evidence(
        summary,
        products,
        customers,
        countries,
        times,
        intersection,
    )

    # ---------------------------------------------------------
    # 8. Rank evidence
    # ---------------------------------------------------------
    ranked_evidence = rank_evidence(evidence)

    # ---------------------------------------------------------
    # 9. Build investigation report
    # ---------------------------------------------------------
    report = build_investigation_report(
        summary,
        ranked_evidence,
    )

    # ---------------------------------------------------------
    # 10. Generate Gemini explanation
    # ---------------------------------------------------------
    explanation = generate_investigation_explanation(
        report
    )

    # ---------------------------------------------------------
    # 11. Return everything
    # ---------------------------------------------------------
    return {
        "report": report,
        "explanation": explanation,
        "evidence": ranked_evidence,
        "summary": summary,
    }