import json


def build_llm_context(
    investigation_report: dict
) -> str:
    """
    Convert the structured investigation report
    into a controlled JSON context for an LLM.

    The LLM receives evidence and computed findings,
    not raw transaction data.
    """

    context = {
        "investigation": investigation_report["investigation"],
        "root_causes": investigation_report["root_causes"],
        "intersection": investigation_report["intersection"],
        "evidence": investigation_report["evidence"],
    }

    return json.dumps(
        context,
        indent=2,
        default=str
    )