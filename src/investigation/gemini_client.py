from google import genai

from src.utils.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    validate_config,
)


FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]


def create_gemini_client():
    """
    Create and return a Gemini API client.
    """

    validate_config()

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    return client


def generate_explanation(
    client,
    prompt: str
) -> str:
    """
    Generate a business explanation using Gemini.

    Automatically falls back to another model
    when the selected model is temporarily unavailable.
    """

    tried_models = []

    for model in FALLBACK_MODELS:

        if model in tried_models:
            continue

        tried_models.append(model)

        try:
            print(f"Trying Gemini model: {model}")

            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )

            return response.text

        except Exception as exc:

            error_text = str(exc)

            is_temporary_unavailable = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "high demand" in error_text.lower()
                or "temporarily unavailable" in error_text.lower()
            )

            if not is_temporary_unavailable:
                raise

            print(
                f"Gemini model {model} unavailable. "
                f"Trying fallback model..."
            )

    raise RuntimeError(
        "All configured Gemini models are temporarily unavailable."
    )