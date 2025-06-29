from datetime import datetime

from ..models import LLMParseResult
from ..utils import denormalize_all_bboxes, get_logger

logger = get_logger(__name__)


def postprocess_llm_response(
    result: LLMParseResult,
    denormalize_images: bool = True,
) -> LLMParseResult:
    """
    Postprocess the LLMParseResult by validating placeholders,
    applying optional bounding box denormalization, and cleaning text.

    This ensures structural consistency between text content and extracted elements,
    and prepares the result for downstream usage or storage.

    Parameters
    ----------
    result : LLMParseResult
        The structured response returned by the LLM.
    denormalize_images : bool, optional
        Whether to convert image bounding boxes from normalized [0.0-1.0]
        to absolute document coordinates.

    Returns
    -------
    LLMParseResult
        The cleaned and validated parsing result.
    """
    text_content = result.parse.text_content or ""

    # --------------------------------------------
    # Step 1a: Validate image placeholders
    # --------------------------------------------
    if result.parse.image_bbox:
        valid_images = {}
        for key, bbox in result.parse.image_bbox.items():
            # Allow both {image_1} and {{image_1}} for robustness
            if f"{{{key}}}" in text_content or f"{{{{{key}}}}}" in text_content:
                valid_images[key] = bbox
            else:
                logger.warning(
                    f"[file: {result.file_name}] [page: {result.page_number}] → "
                    f"Image key '{key}' not found in text_content. Removing."
                )
        result.parse.image_bbox = valid_images

    # --------------------------------------------
    # Step 1b: Validate table placeholders
    # --------------------------------------------
    if result.parse.tables:
        valid_tables = {}
        for key, table in result.parse.tables.items():
            if f"{{{key}}}" in text_content or f"{{{{{key}}}}}" in text_content:
                valid_tables[key] = table
            else:
                logger.warning(
                    f"[file: {result.file_name}] [page: {result.page_number}] → "
                    f"Table key '{key}' not found in text_content. Removing."
                )
        result.parse.tables = valid_tables

    # --------------------------------------------
    # Step 2: Denormalize image bounding boxes (if enabled)
    # --------------------------------------------
    if denormalize_images and result.page_dimensions:
        page_width, page_height = result.page_dimensions
        bbox_dict = result.parse.image_bbox or {}
        result.parse.image_bbox = denormalize_all_bboxes(
            bbox_dict=bbox_dict,
            page_width=page_width,
            page_height=page_height,
        )

    # --------------------------------------------
    # Step 3: Clean text content
    # --------------------------------------------
    result.parse.text_content = text_content.strip()

    # --------------------------------------------
    # Step 4: Clamp confidence score to [0.0, 1.0]
    # --------------------------------------------
    if result.parse.parse_confidence is not None:
        result.parse.parse_confidence = max(
            0.0, min(result.parse.parse_confidence, 1.0)
        )

    # --------------------------------------------
    # Step 5: Fill optional metadata fields if not already set
    # --------------------------------------------
    result.hyperlink_guide = result.hyperlink_guide or None
    result.image_base64 = result.image_base64 or None
    result.tokens_used = result.tokens_used or None
    result.latency_ms = result.latency_ms or None
    result.success = True
    result.error_message = None
    result.timestamp = datetime.utcnow()

    return result
