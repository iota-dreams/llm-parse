from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from .validators import parse_loose_dict


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
    """
    Structured response format for document parsing. The `text_content` field contains
    the main extracted text with placeholder keys (e.g., {{table_1}}, {{image_1}})
    embedded where visual elements occurred. The `tables` and `images` fields provide
    the content for those keys.

    This structure enables clean rendering, post-processing, and semantic indexing.
    """

    text_content: str = Field(
        ...,
        description="Main parsed text with placeholders like {{table_1}}, {{image_2}}"
        "in place of visual content.",
    )
    images: Optional[Dict[str, list[float]]] = Field(
        default_factory=dict,
        description="Dictionary mapping image placeholders (e.g., 'image_1') to "
        "bounding box coordinates: [x_min, y_min, x_max, y_max].",
    )
    tables: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Dictionary mapping table placeholders (e.g., 'table_1') to table"
        "content as HTML or Markdown.",
    )
    parse_confidence: Optional[float] = Field(
        None,
        description="Confidence score (0 to 1) representing certainty of this parsing"
        "result.",
    )

    @field_validator("tables", mode="before")
    @classmethod
    def validate_tables(cls, value):
        return parse_loose_dict(value, field_name="tables")

    @field_validator("images", mode="before")
    @classmethod
    def validate_images(cls, value):
        return parse_loose_dict(value, field_name="images")


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
