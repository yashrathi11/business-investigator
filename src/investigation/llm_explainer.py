from src.investigation.gemini_client import (
    create_gemini_client,
    generate_explanation,
)


SYSTEM_PROMPT = """
You are an AI Business Investigator.

Your job is to explain business anomalies using ONLY the evidence provided
in the investigation context.

Rules:
1. Do not invent facts, numbers, causes, or business events.
2. Clearly distinguish observed evidence from inference.
3. Prioritize the strongest evidence.
4. Explain what happened and how significant it was.
5. Identify likely root causes only when supported by the evidence.
6. If the evidence is insufficient to establish a cause, explicitly say so.
7. Do not claim correlation or causation without evidence.
8. Keep the explanation concise, professional, and business-oriented.

Structure your response as:

1. Executive Summary
2. What Happened
3. Evidence
4. Likely Root Cause
5. Business Impact
6. Recommended Investigation / Action
"""


def build_explanation_prompt(llm_context):
    return f"""
{SYSTEM_PROMPT}

INVESTIGATION CONTEXT:
{llm_context}

Now produce the final business investigation explanation.
"""


def generate_investigation_explanation(investigation_report):
    """
    Generate an evidence-grounded business explanation
    from an investigation report.
    """

    from src.investigation.llm_context_builder import build_llm_context

    llm_context = build_llm_context(investigation_report)
    prompt = build_explanation_prompt(llm_context)

    client = create_gemini_client()

    explanation = generate_explanation(
        client,
        prompt
    )

    return explanation