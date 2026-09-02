import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from analytics.kpi_engine import (
    calculate_revenue,
    calculate_aov,
    calculate_growth,
)


def test_revenue():
    df = pd.DataFrame({
        "Revenue": [100.0, 200.0, 50.0]
    })

    result = calculate_revenue(df)

    assert result == 350.0


def test_aov():
    df = pd.DataFrame({
        "Invoice": ["10001", "10001", "10002"],
        "Revenue": [100.0, 200.0, 50.0]
    })

    result = calculate_aov(df)

    assert result == 175.0


def test_growth():
    assert calculate_growth(120, 100) == 20.0
    assert calculate_growth(80, 100) == -20.0
    assert calculate_growth(100, 100) == 0.0
    assert calculate_growth(100, 0) is None