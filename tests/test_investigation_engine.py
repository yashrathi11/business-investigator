import pandas as pd

from src.investigation.investigation_engine import investigate_anomaly


def test_investigation_engine(monkeypatch):
    def mock_generate_explanation(*args, **kwargs):
        return (
            "Mocked evidence-grounded Gemini explanation for testing. "
            "The investigation pipeline completed successfully."
        )

    monkeypatch.setattr(
        "src.investigation.investigation_engine.generate_investigation_explanation",
        mock_generate_explanation,
    )

    result = investigate_anomaly("2011-12-09")

    assert isinstance(result, dict)

    # Main outputs
    assert "report" in result
    assert "explanation" in result
    assert "evidence" in result
    assert "summary" in result

    # Investigation report
    report = result["report"]

    assert "investigation" in report
    assert "root_causes" in report
    assert "intersection" in report
    assert "evidence" in report

    # Anomaly information
    investigation = report["investigation"]

    assert investigation["severity"] == "CRITICAL"
    assert investigation["actual_revenue"] > 0
    assert investigation["expected_revenue"] > 0
    assert investigation["revenue_deviation_pct"] > 200

    # Evidence
    evidence = result["evidence"]

    assert isinstance(evidence, pd.DataFrame)
    assert len(evidence) > 0

    # Gemini explanation contract
    assert isinstance(result["explanation"], str)
    assert len(result["explanation"].strip()) > 0
    assert "Mocked" in result["explanation"]
