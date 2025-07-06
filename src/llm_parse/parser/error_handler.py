import traceback
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image

from llm_parse.models import ImageRepresentation, LLMConfig, LLMParseResult
from llm_parse.utils import (
    encode_image_to_base64,
    ensure_output_dir,
    get_logger,
    save_model,
)

from .response_builder import build_llm_parse_result

logger = get_logger(__name__)


def handle_llm_failure(
    file_name: str,
    page_number: int,
    total_pages: int,
    parser_config: LLMConfig,
    image: Image.Image,
    pdf_page_dimensions: Tuple[float, float],
    image_bbox_guide: Optional[Dict[str, list[float]]] = None,
    output_dir: Optional[str] = "",
    write_to_disk: bool = False,
    return_images: str = "base64",
    error: Optional[Exception] = None,
) -> LLMParseResult:
    """
    Handles an LLM failure by logging the error and saving partial metadata
    (if required).
    Returns a fallback LLMParseResult with error information populated.
    """
    # Create a concise, readable error message
    error_message = (
        f"{type(error).__name__}: {str(error)}" if error else "Unknown Error"
    )

    # Log a clear, concise error in INFO/ERROR level
    logger.error(f"❌ Error while processing page {page_number}: {error_message}")

    # Log full traceback for debugging (in DEBUG level)
    logger.debug(traceback.format_exc())

    # Build fallback object with a clean, readable message
    fallback = build_llm_parse_result(
        parser_config=parser_config,
        llm_parse=None,  # No structured parse available
        file_name=file_name,
        page_number=page_number,
        total_pages=total_pages,
        image=image,
        pdf_page_dimensions=pdf_page_dimensions,
        image_bbox_guide=image_bbox_guide,
        success=False,
        error_message=error_message,
    )

    if write_to_disk:
        filename = file_name.replace(".", "_")
        page_tag = f"page_{page_number:03d}"
        output_dir_path = Path(output_dir or ".") / filename / page_tag
        output_dir_path = ensure_output_dir(output_dir_path)

        if output_dir_path:
            try:
                fallback_path = output_dir_path / "response.json"
                save_model(model=fallback, output_path=fallback_path)
                logger.info(f"📄 Fallback JSON saved at {fallback_path}")

                if return_images != "none":
                    img_path = output_dir_path / "fallback_page.png"
                    image.save(img_path)
                    logger.info(f"🖼️ Fallback image saved at {img_path}")

                    if return_images == "base64":
                        fallback.image_crops = [
                            ImageRepresentation(
                                key="fallback_page",
                                base64=encode_image_to_base64(image),
                                path=str(img_path),
                                size=image.size,
                                format="png",
                            )
                        ]
            except Exception as save_error:
                logger.warning(f"⚠️ Failed to save fallback output: {save_error}")

    return fallback
