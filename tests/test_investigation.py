import sys

sys.path.insert(0, "src")

import pandas as pd

from investigation.product_contribution import (
    calculate_product_contribution
)
from investigation.customer_contribution import (
    calculate_customer_contribution
)
from investigation.country_contribution import (
    calculate_country_contribution
)
from investigation.time_contribution import (
    calculate_time_contribution
)
from investigation.intersection_analysis import (
    analyze_anomaly_intersection
)
from investigation.root_cause_ranker import (
    rank_root_causes
)
from investigation.investigation_summary import (
    build_investigation_summary
)


def create_test_data():
    return pd.DataFrame({
        "Invoice": [
            "1001",
            "1002",
            "1003",
            "1004"
        ],
        "StockCode": [
            "A",
            "A",
            "B",
            "B"
        ],
        "Description": [
            "Product A",
            "Product A",
            "Product B",
            "Product B"
        ],
        "Quantity": [
            10,
            20,
            5,
            10
        ],
        "InvoiceDate": pd.to_datetime([
            "2011-12-09 09:00:00",
            "2011-12-09 10:00:00",
            "2011-12-09 09:00:00",
            "2011-12-10 09:00:00"
        ]),
        "Price": [
            10.0,
            10.0,
            20.0,
            20.0
        ],
        "Customer ID": [
            100,
            100,
            200,
            200
        ],
        "Country": [
            "United Kingdom",
            "United Kingdom",
            "Germany",
            "Germany"
        ],
        "Revenue": [
            100.0,
            200.0,
            100.0,
            200.0
        ]
    })


def test_product_contribution():
    df = create_test_data()

    result = calculate_product_contribution(
        df,
        "2011-12-09"
    )

    assert not result.empty
    assert result.iloc[0]["StockCode"] == "A"
    assert result.iloc[0]["revenue"] == 300.0


def test_customer_contribution():
    df = create_test_data()

    result = calculate_customer_contribution(
        df,
        "2011-12-09"
    )

    assert not result.empty
    assert result.iloc[0]["Customer ID"] == 100
    assert result.iloc[0]["revenue"] == 300.0


def test_country_contribution():
    df = create_test_data()

    result = calculate_country_contribution(
        df,
        "2011-12-09"
    )

    assert not result.empty
    assert result.iloc[0]["Country"] == "United Kingdom"
    assert result.iloc[0]["revenue"] == 300.0


def test_time_contribution():
    df = create_test_data()

    result = calculate_time_contribution(
        df,
        "2011-12-09"
    )

    assert not result.empty
    assert result.iloc[0]["hour"] == 9
    assert result.iloc[0]["revenue"] == 200.0


def test_intersection_analysis():
    df = create_test_data()

    result = analyze_anomaly_intersection(
        df,
        "2011-12-09",
        customer_id=100,
        country="United Kingdom",
        hour=9
    )

    assert not result.empty
    assert result.iloc[0]["revenue"] == 100.0
    assert result.iloc[0]["orders"] == 1


def test_root_cause_ranker():
    df = create_test_data()

    product = calculate_product_contribution(
        df,
        "2011-12-09"
    )

    customer = calculate_customer_contribution(
        df,
        "2011-12-09"
    )

    country = calculate_country_contribution(
        df,
        "2011-12-09"
    )

    time = calculate_time_contribution(
        df,
        "2011-12-09"
    )

    result = rank_root_causes(
        product,
        customer,
        country,
        time
    )

    assert not result.empty
    assert "dimension" in result.columns
    assert "contribution_pct" in result.columns


def test_investigation_summary():
    df = create_test_data()

    product = calculate_product_contribution(
        df,
        "2011-12-09"
    )

    customer = calculate_customer_contribution(
        df,
        "2011-12-09"
    )

    country = calculate_country_contribution(
        df,
        "2011-12-09"
    )

    time = calculate_time_contribution(
        df,
        "2011-12-09"
    )

    intersection = analyze_anomaly_intersection(
        df,
        "2011-12-09",
        customer_id=100,
        country="United Kingdom",
        hour=9
    )

    anomaly_row = pd.Series({
        "InvoiceDate": pd.Timestamp("2011-12-09"),
        "revenue": 500.0,
        "rolling_mean_30": 200.0,
        "z_score": 4.0,
        "severity": "CRITICAL",
        "revenue_deviation": 300.0,
        "revenue_deviation_pct": 150.0
    })

    result = build_investigation_summary(
        anomaly_row,
        product,
        customer,
        country,
        time,
        intersection
    )

    assert result["anomaly_date"] == "2011-12-09 00:00:00"
    assert result["severity"] == "CRITICAL"
    assert result["top_product"] is not None
    assert result["top_customer"] is not None
    assert result["top_country"] is not None
    assert result["top_hour"] is not None
    assert result["intersection"] is not None