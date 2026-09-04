import pandas as pd
import shap


def calculate_shap_values(
    model,
    X: pd.DataFrame
):
    """
    Calculate SHAP values for an XGBoost model.
    """

    explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(X)

    return explainer, shap_values


def calculate_feature_importance(
    shap_values,
    feature_names
):
    """
    Calculate mean absolute SHAP importance
    for each feature.
    """

    importance = (
        pd.DataFrame({
            "feature": feature_names,
            "importance": abs(shap_values).mean(axis=0)
        })
        .sort_values(
            "importance",
            ascending=False
        )
        .reset_index(drop=True)
    )

    return importance


def plot_shap_summary(
    shap_values,
    X: pd.DataFrame
):
    """
    Plot SHAP feature importance summary.
    """

    shap.summary_plot(
        shap_values,
        X,
        show=True
    )