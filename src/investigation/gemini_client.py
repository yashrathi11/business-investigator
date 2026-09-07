from google import genai

from src.utils.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    validate_config,
)


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
    """

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    return response.text