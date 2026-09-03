import pandas as pd


def calculate_revenue_baseline(
    daily_metrics: pd.DataFrame,
    window: int = 30
) -> pd.DataFrame:
    """
    Calculate previous-period rolling revenue baseline.
    The current day's revenue is excluded from the baseline.
    """
    df = daily_metrics.copy()

    df = df.sort_values("InvoiceDate").reset_index(drop=True)

    df["rolling_mean_30"] = (
        df["revenue"]
        .rolling(window=window)
        .mean()
        .shift(1)
    )

    df["rolling_std_30"] = (
        df["revenue"]
        .rolling(window=window)
        .std()
        .shift(1)
    )

    df["z_score"] = (
        (df["revenue"] - df["rolling_mean_30"])
        / df["rolling_std_30"]
    )

    return df


def detect_revenue_anomalies(
    baseline: pd.DataFrame,
    z_threshold: float = 3.0
) -> pd.DataFrame:
    """
    Flag revenue observations as anomalies using Z-score.
    """

    df = baseline.copy()

    df["is_anomaly"] = (
        df["z_score"].abs() >= z_threshold
    )

    return df

def assign_anomaly_severity(anomalies: pd.DataFrame) -> pd.DataFrame:
    """
    Assign severity based on absolute Z-score.
    """
    df = anomalies.copy()

    def get_severity(z_score):
        if pd.isna(z_score):
            return "NORMAL"

        z = abs(z_score)

        if z < 2:
            return "NORMAL"
        elif z < 3:
            return "MEDIUM"
        elif z < 4:
            return "HIGH"
        else:
            return "CRITICAL"

    df["severity"] = df["z_score"].apply(get_severity)

    return df

def calculate_revenue_impact(anomalies: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate revenue deviation from the historical baseline.
    """
    df = anomalies.copy()

    df["revenue_deviation"] = (
        df["revenue"] - df["rolling_mean_30"]
    )

    df["revenue_deviation_pct"] = (
        df["revenue_deviation"]
        / df["rolling_mean_30"]
    ) * 100

    return df

def plot_revenue_anomalies(anomalies: pd.DataFrame):
    """
    Plot actual revenue against the historical 30-day baseline
    and highlight detected anomalies.
    """
    import matplotlib.pyplot as plt

    df = anomalies.copy()

    plt.figure(figsize=(14, 6))

    plt.plot(
        df["InvoiceDate"],
        df["revenue"],
        label="Actual Revenue"
    )

    plt.plot(
        df["InvoiceDate"],
        df["rolling_mean_30"],
        label="30-Day Baseline"
    )

    anomaly_points = df[df["is_anomaly"]]

    plt.scatter(
        anomaly_points["InvoiceDate"],
        anomaly_points["revenue"],
        label="Anomalies"
    )

    plt.title("Daily Revenue vs Historical Baseline")
    plt.xlabel("Date")
    plt.ylabel("Revenue (£)")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.show()

def detect_multivariate_anomalies(
    daily_metrics: pd.DataFrame,
    contamination: float = 0.02,
    random_state: int = 42
) -> pd.DataFrame:
    """
    Detect multivariate business anomalies using Isolation Forest.
    """

    from sklearn.ensemble import IsolationForest

    df = daily_metrics.copy()

    features = [
        "revenue",
        "orders",
        "aov",
        "customers",
        "units_sold"
    ]

    model_data = df[features].copy()

    model = IsolationForest(
        contamination=contamination,
        random_state=random_state
    )

    predictions = model.fit_predict(model_data)
    scores = model.decision_function(model_data)

    df["is_multivariate_anomaly"] = predictions == -1
    df["isolation_score"] = scores

    return df


def combine_anomaly_results(
    statistical: pd.DataFrame,
    multivariate: pd.DataFrame
) -> pd.DataFrame:
    """
    Combine statistical and multivariate anomaly detection results.
    """

    stat_cols = [
        "InvoiceDate",
        "revenue",
        "rolling_mean_30",
        "rolling_std_30",
        "z_score",
        "is_anomaly",
        "severity",
        "revenue_deviation",
        "revenue_deviation_pct"
    ]

    multi_cols = [
        "InvoiceDate",
        "is_multivariate_anomaly",
        "isolation_score"
    ]

    stat = statistical[stat_cols].copy()
    multi = multivariate[multi_cols].copy()

    result = stat.merge(
        multi,
        on="InvoiceDate",
        how="left"
    )

    result["final_anomaly"] = (
        result["is_anomaly"]
        | result["is_multivariate_anomaly"]
    )

    return result
