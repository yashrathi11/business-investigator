import pandas as pd


def rank_evidence(
    evidence: pd.DataFrame
) -> pd.DataFrame:
    """
    Rank investigation evidence by business strength.

    Priority:
        critical > high > medium > low
    """

    result = evidence.copy()

    strength_scores = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1
    }

    result["strength_score"] = (
        result["strength"]
        .str.lower()
        .map(strength_scores)
        .fillna(0)
    )

    result = result.sort_values(
        ["strength_score", "evidence_type"],
        ascending=[False, True]
    ).reset_index(drop=True)

    result["evidence_rank"] = (
        result.index + 1
    )

    return result