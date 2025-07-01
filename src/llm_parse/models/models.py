from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator

from .validators import parse_loose_dict


class SafetySetting(BaseModel):
    category: str
    threshold: str


class TableHandler(str, Enum):
    markdown = "markdown"
    html = "html"


class ImageRepresentation(BaseModel):
    """
    A unified representation of a cropped image in a parsing response.
    """

    # e.g., "image_1"
    key: str
    path: Optional[str] = None
    base64: Optional[str] = None
    format: Optional[str] = "png"
    # width, height
    size: Optional[Tuple[int, int]] = None
    caption: Optional[str] = None


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
    Structured response format for document parsing.

    - `text_content`: Extracted text with placeholders like {{table_1}}, {{image_1}}.
    - `tables`: Mapping of placeholders to table content in HTML or Markdown.
    - `image_bbox`: Mapping of placeholders to image bounding boxes.
    - `parse_confidence`: Confidence score from 0 to 1.

    This structure enables clean rendering, post-processing, and semantic indexing.
    """

    text_content: str = Field(
        ...,
        description="Main parsed text with placeholders like {{table_1}}, {{image_2}}"
        "in place of visual content.",
    )
    image_bbox: Optional[Dict[str, list[float]]] = Field(
        default_factory=dict,
        description="Dictionary mapping image placeholders (e.g., 'image_1') to "
        "bounding box coordinates: [x_min, y_min, x_max, y_max].",
    )
    tables: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Dictionary mapping table placeholders (e.g., 'table_1') to table "
        "content as {{table_format}} (HTML or Markdown).",
    )
    parse_confidence: Optional[float] = Field(
        None,
        description="Confidence score (0 to 1) representing certainty of this parsing"
        "result.",
    )

    @field_validator("tables", mode="before")
    @classmethod
    def validate_tables(cls, value):
        # Allow null-like values from LLMs such as None, "null", or empty string
        # These are normalized into an empty dictionary to prevent validation failure
        if value in (None, "null", ""):
            return {}

        # Attempt to parse JSON or Python-style stringified dicts using utility
        return parse_loose_dict(value, field_name="tables")

    @field_validator("image_bbox", mode="before")
    @classmethod
    def validate_images(cls, value):
        # Same null/empty defensive guard for image_bbox
        if value in (None, "null", ""):
            return {}

        # Use robust parsing for stringified or malformed dicts
        return parse_loose_dict(value, field_name="image_bbox")


class LLMParseResult(BaseModel):
    """
    Encapsulates the full result of a document parsing run using an LLM.

    This includes the actual parsed content (`LLMParse`), metadata about the file and
    page processed, guidance used for rendering or cropping
    (like bounding boxes or hyperlinks),resource usage, timing, and overall
    success status.
    """

    config: LLMConfig = Field(
        ...,
        description="Configuration used for the LLM parsing request.",
    )

    parse: LLMParse = Field(
        ...,
        description="Structured parsing result including text, tables, and image"
        "references.",
    )

    file_name: str = Field(
        ...,
        description="Name of the input file from which this content was parsed.",
    )

    page_number: int = Field(
        ...,
        description="1-based index of the page parsed in the source document.",
    )

    total_pages: Annotated[int, Field(ge=1)] = Field(
        default=1,
        description="Total number of pages in the input document.",
    )

    image_crops: Optional[List[ImageRepresentation]] = Field(
        default=None,
        description="List of structured representations for each cropped image region, "
        "containing both base64 and/or path depending on configuration.",
    )

    image_bbox_guide: Optional[Dict[str, List[float]]] = Field(
        default=None,
        description="Optional guidance obtained from PyMuPDF for image bounding boxes "
        "(e.g., for cropping). Keys are placeholders like 'image_1', and values are "
        "[x_min, y_min, x_max, y_max].",
    )

    image_description: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional dictionary mapping image placeholders (e.g., 'image_1') "
        "to their natural language descriptions.",
    )

    hyperlink_guide: Optional[List[str]] = Field(
        default=None,
        description="List of hyperlinks (if any) extracted using PyMuPDF"
        "or associated with the parsed page.",
    )

    page_dimensions: Optional[Tuple[float, float]] = Field(
        default=None,
        description="Dimensions of the image representation of the page in points or "
        "pixels, as (width, height)."
        "(Image.open(io.BytesIO(page.get_pixmap(dpi=300).tobytes('png'))))",
    )

    pdf_page_dimensions: Optional[Tuple[float, float]] = Field(
        default=None,
        description="Dimensions of the original page (as pdf) in points or pixels, as "
        "(width, height). (page.rect.width and page.rect.height)",
    )

    tokens_used: Optional[int] = Field(
        default=None,
        description="Total number of LLM tokens consumed during parsing.",
    )

    latency_ms: Optional[float] = Field(
        default=None,
        description="Time taken (in milliseconds) to process this parse.",
    )

    success: bool = Field(
        default=True,
        description="Indicates whether the parsing operation succeeded.",
    )

    error_message: Optional[str] = Field(
        default=None,
        description="Error message if parsing failed. Present only when `success`"
        "is False.",
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the parsing result was generated.",
    )
