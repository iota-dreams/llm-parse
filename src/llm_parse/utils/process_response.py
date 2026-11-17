import ast
import json
from typing import Any, Dict

from ..utils import get_logger

logger = get_logger(__name__)


def parse_raw_llm_response(raw_response: str) -> Dict[str, Any]:
    """
    Safely parse a raw LLM response string into a structured dictionary.

    This function handles malformed or improperly formatted LLM responses by:
    - Removing markdown code fences (e.g. ```json)
    - Attempting strict JSON decoding first
    - Falling back to `ast.literal_eval` after unescaping improperly escaped quotes

    Designed to tolerate poor formatting typical in LLM outputs
    (e.g. escaped HTML blocks).

    Args:
        raw_response (str): The raw string response returned by the LLM.

    Returns:
        Dict[str, Any]: A sanitized dictionary suitable for downstream Pydantic
        validation.

    Raises:
        ValueError: If all parsing strategies fail or the output is not a dictionary.
    """
    logger.debug("Received raw LLM response for sanitization")

    if not isinstance(raw_response, str):
        raise ValueError(f"Expected string input, got {type(raw_response).__name__}")

    cleaned = raw_response.strip()

    # Remove markdown-style code block markers (e.g., ```json ... ```)
    if cleaned.startswith("```") and cleaned.endswith("```"):
        logger.info("Detected markdown code fences in LLM response. Stripping them...")
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        )

    # --- First Attempt: Strict JSON parsing ---
    try:
        parsed_json = json.loads(cleaned)
        if not isinstance(parsed_json, dict):
            raise ValueError("Top-level JSON value is not a dictionary")
        logger.info("Successfully parsed LLM response as JSON")
        return parsed_json
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed: {e}")

    # --- Fallback: Try ast.literal_eval after unescaping escaped quotes ---
    try:
        logger.info("Attempting fallback parsing via ast.literal_eval")
        unescaped = cleaned.replace('\\"', '"')

        # literal_eval only supports expressions, not control characters
        parsed_ast = ast.literal_eval(unescaped)
        if not isinstance(parsed_ast, dict):
            raise ValueError("Parsed AST result is not a dictionary")

        logger.info("Successfully parsed LLM response using ast.literal_eval")
        return parsed_ast

    except (ValueError, SyntaxError) as e:
        logger.error("Both JSON and literal_eval parsing failed", exc_info=True)
        raise ValueError(f"Failed to parse LLM response: {e}") from e


def normalize_llm_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures the parsed LLM output dictionary contains valid fields
    and replaces null-like placeholders with default values.

    Currently focuses on:
    - `tables`: sets to empty dict if None/"null"/empty string
    - `image_bbox`: sets to empty dict if None/"null"/empty string

    Parameters
    ----------
    data : dict
        Parsed dictionary from the LLM response.

    Returns
    -------
    dict
        The cleaned and normalized dictionary.
    """
    for key in ("tables", "image_bbox"):
        val = data.get(key)
        if val in (None, "null", ""):
            logger.debug(f"Normalizing null value in LLM field: '{key}' → {{}}")
            data[key] = {}
    return data
