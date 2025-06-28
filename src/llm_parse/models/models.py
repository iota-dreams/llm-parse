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
    """Response format expected from the LLM parser."""

    text_content: str = Field(
        ...,
        description="Main text content extracted from the image or document. Should be"
        "clean and ready for downstream processing.",
    )
    image_bbox: Optional[List[List[float]]] = Field(
        None,
        description="List of bounding boxes for visual elements detected. Each box is "
        "[x_min, y_min, x_max, y_max].",
    )
    table_extracted: Optional[Union[str, None]] = Field(
        None,
        description="Extracted table content, formatted as HTML or Markdown.",
    )
    parse_confidence: Optional[float] = Field(
        None,
        description="Optional confidence score (0 to 1) indicating how certain the"
        " model is about its parsing.",
    )


class LLMParseResult(BaseModel):
    """
    Output of the LLM parser along with metadata and config used.
    """

    config: LLMConfig  # The config that was used to make the call
    parse: LLMParse  # The actual parsed result
    image_base64: Optional[List[str]] = None  # list of base64-encoded image strings
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
