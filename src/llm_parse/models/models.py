from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class SafetySetting(BaseModel):
    category: str
    threshold: str


class LLMConfig(BaseModel):
    """
    Configuration for the LLM model.
    """

    provider: str  # "anthropi", "google_gemini", "google_genai", "openai"  Refer this: https://python.langchain.com/docs/integrations/chat/
    model_name: str
    temperature: Optional[float] = 0.7
    prompt: str  # Base system or task prompt
    image_path: Optional[Union[str, Path]] = None
    table_type: Optional[str] = "html"
    safety_settings: Optional[List[SafetySetting]] = None


class LLMParse(BaseModel):
    """Response format expected from the LLM parser"""

    text_content: str
    image_bbox: Optional[List[List[float]]] = None  # List of bounding boxes
    table_extracted: Optional[Union[str, None]] = None  # markdown or HTML as string
    image_base64: Optional[List[str]] = None  # list of base64-encoded image strings


class LLMParseResult(BaseModel):
    """
    Output of the LLM parser along with metadata and config used.
    """

    config: LLMConfig  # The config that was used to make the call
    parse: LLMParse  # The actual parsed result

    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
