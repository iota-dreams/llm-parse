from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel


class LLMConfig(BaseModel):
    """
    Configuration for the LLM model.
    """

    provider: str  # "gpt", "gemini", "claude"
    model_name: str
    temperature: Optional[float] = 0.7
    prompt: str  # Base system or task prompt
    image_path: Optional[Union[str, Path]] = None
