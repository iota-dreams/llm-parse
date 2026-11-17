import ast
import json
import re
from typing import Any


def _fix_unescaped_newlines(value: str) -> str:
    """
    Attempts to escape unescaped newlines inside JSON string values.
    Applies only within double-quoted values.
    """

    def replacer(match):
        inner = match.group(1)
        escaped = inner.replace("\n", "\\n").replace('"', '\\"')
        return f'"{escaped}"'

    return re.sub(r'"([^"]*?\n[^"]*?)"', replacer, value)


def parse_loose_dict(value: Any, field_name: str = "field") -> dict:
    """
    Parses a value into a dictionary.

    Accepts:
    - A valid Python dict (no-op)
    - A JSON string (with optional newline fixing)
    - A Python-style stringified dict (via ast.literal_eval)

    Raises:
        TypeError: if input type is invalid
        ValueError: if string cannot be parsed into a dict
    """
    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name}: expected a dict or string, got {type(value).__name__}"
        )

    # Defensive: fix malformed newlines inside JSON strings
    value = _fix_unescaped_newlines(value)

    # Try JSON parsing first
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError(f"{field_name}: JSON value was not a dictionary")
        return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: try literal_eval for Python-style dicts
    try:
        parsed = ast.literal_eval(value)
        if not isinstance(parsed, dict):
            raise ValueError(f"{field_name}: parsed value was not a dictionary")
        return parsed
    except Exception as e:
        raise ValueError(
            f"Invalid '{field_name}' format: expected dict or valid stringified dict."
            f"Error: {e}"
        ) from e
