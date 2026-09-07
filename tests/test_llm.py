import pandas as pd

from src.investigation.llm_context_builder import build_llm_context
from src.investigation.llm_explainer import build_explanation_prompt


def test_llm_context_builder():
    report = {
        "investigation": {
            "anomaly_date": "2011-12-09",
            "severity": "CRITICAL",
            "actual_revenue": 200918.98,
            "expected_revenue": 60084.96,
        },
        "root_causes": {
            "top_product": {
                "description": "PAPER CRAFT , LITTLE BIRDIE",
                "revenue": 168469.60,
            }
        },
        "intersection": {
            "revenue": 168469.60,
            "units_sold": 80995,
            "orders": 1,
        },
        "evidence": [
            {
                "evidence_type": "product",
                "strength": "high",
                "finding": "Product contributed 83.85% of anomaly-day revenue.",
            }
        ],
    }

    context = build_llm_context(report)

    assert isinstance(context, str)
    assert "2011-12-09" in context
    assert "CRITICAL" in context
    assert "PAPER CRAFT" in context
    assert "168469.6" in context


def test_explanation_prompt():
    context = """
    {
        "investigation": {
            "severity": "CRITICAL"
        }
    }
    """

    prompt = build_explanation_prompt(context)

    assert isinstance(prompt, str)
    assert "evidence" in prompt.lower()
    assert "do not invent" in prompt.lower()
    assert context in prompt