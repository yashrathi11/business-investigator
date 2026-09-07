import pandas as pd


def build_investigation_report(
    investigation_summary: dict,
    ranked_evidence: pd.DataFrame
) -> dict:
    """
    Build a structured investigation report from
    the anomaly summary and ranked evidence.
    """

    report = {
        "investigation": {
            "anomaly_date": investigation_summary["anomaly_date"],
            "severity": investigation_summary["severity"],
            "actual_revenue": investigation_summary["actual_revenue"],
            "expected_revenue": investigation_summary["expected_revenue"],
            "revenue_deviation": investigation_summary["revenue_deviation"],
            "revenue_deviation_pct": investigation_summary[
                "revenue_deviation_pct"
            ],
            "z_score": investigation_summary["z_score"],
        },

        "root_causes": {
            "product": investigation_summary["top_product"],
            "customer": investigation_summary["top_customer"],
            "country": investigation_summary["top_country"],
            "time": investigation_summary["top_hour"],
        },

        "intersection": investigation_summary["intersection"],

        "evidence": ranked_evidence.to_dict(
            orient="records"
        ),
    }

    return report