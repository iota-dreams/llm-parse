from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PIL import Image as PILImage

from llm_parse.models import (
    ImageDescription,
    ImageParseData,
    ImageRepresentation,
    LLMConfig,
    LLMParse,
    LLMParseResult,
)

from ..utils import get_logger

logger = get_logger(__name__)


def build_llm_parse_result(
    *,
    llm_parse: Optional[LLMParse],
    parser_config: LLMConfig,
    file_name: str,
    page_number: int,
    total_pages: int,
    image: PILImage.Image,
    pdf_page_dimensions: Tuple[float, float],
    image_bbox_guide: Optional[Dict[str, list]] = None,
    image_description: Optional[Dict[str, ImageDescription]] = None,
    image_description_config: Optional[LLMConfig] = None,
    image_crops: Optional[List[ImageRepresentation]] = None,
    hyperlink_guide: Optional[List[str]] = None,
    image_data: Optional[ImageParseData] = None,
    success: bool = True,
    error_message: Optional[BaseException] = None,
) -> LLMParseResult:
    """
    Constructs a complete LLMParseResult object from the given inputs.

    Ensures consistent schema whether the parse was successful or failed.

    Parameters
    ----------
    llm_parse : Optional[LLMParse]
        Parsed result from the LLM. If None, a default empty parse is used.
    parser_config : LLMConfig
        Configuration used for the LLM call.
    file_name : str
        Name of the source file.
    page_number : int
        1-based index of the page being parsed.
    total_pages : int
        Total number of pages in the document.
    image : PIL.Image
        Rendered image of the page.
    pdf_page_dimensions : Tuple[float, float]
        PDF-native page dimensions as (width, height).
    image_bbox_guide : Optional[Dict[str, list]]
        Bounding box guidance, used only if image_data is not passed.
    image_description : Optional[Dict[str, ImageDescription]]
        VLM-generated descriptions for cropped image regions.
    image_description_config : Optional[LLMConfig]
        LLM config used to generate image descriptions.
    image_crops : Optional[List[ImageRepresentation]]
    Structured representations for cropped image regions,
    including base64 strings or file paths, dimensions, and format.
    hyperlink_guide : Optional[List[str]]
        List of extracted hyperlinks (if any).
    image_data : Optional[ImageParseData]
        If provided, overrides image-related metadata construction.
    success : bool
        Indicates whether the parse succeeded.
    error_message : Optional[BaseException]
        Exception raised during parsing, if any.

    Returns
    -------
    LLMParseResult
        A fully assembled result object.
    """

    if not llm_parse:
        logger.warning(
            "No LLMParse provided for page %d of '%s'. Using fallback.",
            page_number,
            file_name,
        )
        llm_parse = LLMParse(
            text_content="",
            image_bbox={},
            tables={},
            parse_confidence=0.0,
        )

    # Build image_data if not explicitly passed
    if image_data is None and (
        image_bbox_guide or image_description or image_description_config or image_crops
    ):
        logger.debug(
            "Constructing ImageParseData from available inputs for page %d.",
            page_number,
        )
        image_data = ImageParseData(
            bbox_guide=image_bbox_guide,
            descriptions=image_description,
            description_config=image_description_config,
            crops=image_crops,
        )
    elif image_data and image_crops:
        logger.debug(
            "Updating ImageParseData with image_crops for page %d.", page_number
        )
        image_data.crops = image_crops

    formatted_error = (
        f"{type(error_message).__name__}: {str(error_message)}"
        if error_message
        else None
    )

    logger.info(
        "Building LLMParseResult for file='%s', page=%d/%d, success=%s",
        file_name,
        page_number,
        total_pages,
        success,
    )

    return LLMParseResult(
        parser_config=parser_config,
        parse=llm_parse,
        file_name=file_name,
        page_number=page_number,
        total_pages=total_pages,
        page_dimensions=(image.width, image.height),
        pdf_page_dimensions=pdf_page_dimensions,
        image_data=image_data,
        hyperlink_guide=hyperlink_guide,
        success=success,
        error_message=formatted_error,
        timestamp=datetime.utcnow(),
    )
