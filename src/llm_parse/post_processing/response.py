from datetime import datetime
from typing import Dict, List, Optional

from ..models import LLMParseResult
from ..utils import denormalize_all_bboxes, get_logger

logger = get_logger(__name__)


def postprocess_page_parse_result(
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
    result.tokens_used = result.tokens_used or None
    result.latency_ms = result.latency_ms or None
    result.timestamp = datetime.utcnow()

    return result


def postprocess_document_parse_results(
    parsed_results: List[LLMParseResult],
    prefer_file_path: bool = True,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
) -> Dict:
    """
    Post-processes a list of `LLMParseResult` objects and converts them into a flat,
    concatenated RAG-ready format.

    This function combines text content from all pages into a single string, and
    processes image and table placeholders into appropriate Markdown references.

    Parameters
    ----------
    parsed_results : List[LLMParseResult]
        List of parsed document page results from the LLM pipeline.
    prefer_file_path : bool, optional
        Whether to prefer file paths over base64 for image references. Defaults to True.
    start_page : Optional[int], optional
        The starting page number of the parsed document range. Defaults to None.
    end_page : Optional[int], optional
        The ending page number of the parsed document range. Defaults to None.


    Returns
    -------
    Dict
        A dictionary containing the following keys:
        - `file_name`: The name of the parsed document file.
        - `llm_config`: The configuration used for parsing.
        - `text_content`: The combined markdown text from all pages, including
        inlinedtables and image references.
        - `images`: A dictionary mapping image keys (e.g., "image_1") to their file
        paths or base64 strings.
        - `image_descriptions`: A dictionary mapping image keys to their descriptions
        (if available).
        - `skipped_pages`: List of page numbers that failed parsing.
        - `errors`: Dictionary mapping skipped page numbers to error messages.
        - `token_count`: Total number of tokens used across all pages.
        - `timestamp`: UTC timestamp when this result was generated.

    Notes
    -----
    - Images are rendered in markdown format. If `prefer_file_path` is True, file paths
      are used for the `src` attribute. Otherwise, image keys are included.
    - Image descriptions are inserted after the image markdown with a
    `**Image description:**` prefix, which helps RAG systems reason over visual content.
    - Tables are inlined directly into the `text_content`, replacing placeholders.
    - If a page fails parsing (`success=False`), it is skipped and noted in the
    `skipped_pages` and `errors` sections.
    - The final output is flattened and does not include per-page segmentation, making
    it more suitable for downstream RAG applications.
    """
    final_text = []
    images: Dict[str, Dict[str, str]] = {}
    skipped_pages: List[int] = []
    errors: Dict[int, str] = {}
    token_count = 0

    file_name = None
    llm_config = None

    for result in parsed_results:
        if not result.success:
            logger.warning(
                f"Skipping page {result.page_number} due to error: "
                f"{result.error_message}"
            )
            skipped_pages.append(result.page_number)
            errors[result.page_number] = result.error_message or "Unknown error"
            continue

        try:
            file_name = file_name or result.file_name
            llm_config = llm_config or result.parser_config
            token_count += result.tokens_used or 0

            content = result.parse.text_content

            # Inline tables
            if result.parse.tables:
                for key, table in result.parse.tables.items():
                    placeholder = f"{{{key}}}"  # Matches {table_1}
                    content = content.replace(placeholder, table)

            # Inline image markdown with filenames or fallback keys
            if result.image_data and result.image_data.crops:
                for image in result.image_data.crops:
                    key = image.key

                    # Determine the image reference key to use in markdown and
                    # dictionary
                    if prefer_file_path and image.path:
                        ref_key = str(image.path)
                    else:
                        # Fallback key construction if no path available or
                        # prefer_file_path is False
                        ref_key = (
                            f"{result.file_name}_page_{result.page_number:03d}_"
                            f"{key}"
                        )

                    # Markdown uses ref_key for src
                    image_md = f"![{key}]({ref_key})"

                    # Optional description for the image
                    description = ""
                    if (
                        result.image_data.descriptions
                        and key in result.image_data.descriptions
                    ):
                        desc_obj = result.image_data.descriptions[key]
                        if desc_obj and getattr(desc_obj, "description", None):
                            description = desc_obj.description

                    # Replace placeholder in text_content with markdown + description
                    # (if any)
                    image_description_md = (
                        f"  \n**Image description:** {description}"
                        if description
                        else ""
                    )
                    content = content.replace(
                        f"{{{key}}}", f"{image_md}{image_description_md}"
                    )

                    # Store base64 string or empty string if missing
                    base64_str = image.base64 or ""

                    # Store image info keyed by the reference key (path or fallback)
                    images[ref_key] = {
                        "base64": base64_str,
                        "description": description,
                    }

            final_text.append(content)

        except Exception as e:
            logger.exception(f"Failed to post-process page {result.page_number}: {e}")
            skipped_pages.append(result.page_number)
            errors[result.page_number] = str(e)

    return {
        "file_name": file_name,
        "llm_config": llm_config,
        "text_content": "\n\n".join(final_text).strip(),
        "images": images,
        "skipped_pages": skipped_pages,
        "errors": errors,
        "token_count": token_count,
        "timestamp": datetime.utcnow().isoformat(),
        "start_page": start_page,
        "end_page": end_page,
    }
