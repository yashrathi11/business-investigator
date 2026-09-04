import pandas as pd
from scipy.stats import ttest_1samp


def compare_anomaly_period(
    transactions: pd.DataFrame,
    anomaly_date,
    baseline_days: int = 30
):
    """
    Compare revenue during an anomaly day against
    the preceding baseline period.

    Returns:
        dict containing baseline statistics,
        anomaly-day revenue, t-test result,
        and statistical significance.
    """

    df = transactions.copy()

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    anomaly_date = pd.to_datetime(anomaly_date).normalize()

    # Daily revenue
    daily_revenue = (
        df.groupby(df["InvoiceDate"].dt.normalize())["Revenue"]
        .sum()
        .sort_index()
    )

    # Previous baseline period
    baseline_end = anomaly_date - pd.Timedelta(days=1)
    baseline_start = (
        baseline_end - pd.Timedelta(days=baseline_days - 1)
    )

    baseline = daily_revenue.loc[
        baseline_start:baseline_end
    ].dropna()

    anomaly_revenue = daily_revenue.get(
        anomaly_date,
        0
    )

    if len(baseline) == 0:
        return {
            "anomaly_date": anomaly_date,
            "anomaly_revenue": anomaly_revenue,
            "baseline_mean": None,
            "baseline_std": None,
            "t_statistic": None,
            "p_value": None,
            "is_significant": False,
        }

    # Compare anomaly-day revenue against baseline distribution
    test_result = ttest_1samp(
        baseline,
        popmean=anomaly_revenue
    )

    p_value = float(test_result.pvalue)

    return {
        "anomaly_date": anomaly_date,
        "anomaly_revenue": float(anomaly_revenue),
        "baseline_mean": float(baseline.mean()),
        "baseline_std": float(baseline.std()),
        "t_statistic": float(test_result.statistic),
        "p_value": p_value,
        "is_significant": p_value < 0.05,
    }