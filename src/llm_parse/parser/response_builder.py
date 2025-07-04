from typing import Dict, Optional, Tuple

from PIL import Image as PILImage

from llm_parse.models import (
    ImageDescription,
    LLMConfig,
    LLMParse,
    LLMParseResult,
)


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
    success: bool = True,
    error_message: Optional[str] = None,
) -> LLMParseResult:
    """
    Centralized builder for LLMParseResult to ensure consistency across
    success and fallback/error cases.

    Parameters
    ----------
    llm_parse : Optional[LLMParse]
        Parsed result from LLM. Can be None in case of fallback.
    ... all other parameters as needed to construct the result

    Returns
    -------
    LLMParseResult
        Fully populated result object.
    """
    return LLMParseResult(
        parser_config=parser_config,
        parse=llm_parse
        or LLMParse(text_content="", image_bbox={}, tables={}, parse_confidence=0.0),
        file_name=file_name,
        page_number=page_number,
        total_pages=total_pages,
        page_dimensions=(image.width, image.height),
        pdf_page_dimensions=pdf_page_dimensions,
        image_bbox_guide=image_bbox_guide,
        image_description=image_description,
        image_description_config=image_description_config,
        success=success,
        error_message=str(error_message) if error_message else None,
    )
