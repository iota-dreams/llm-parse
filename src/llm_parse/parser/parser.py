import os
import traceback
from pathlib import Path
from typing import List, Literal, Optional

from llm_parse.file_handlers import PDFHandler
from llm_parse.llm.dispatcher import dispatch_llm_request
from llm_parse.models import (
    ImageRepresentation,
    LLMConfig,
    LLMParse,
    LLMParseResult,
    TableHandler,
)
from llm_parse.post_processing import postprocess_llm_response
from llm_parse.utils import (
    annotate_image_with_bbox,
    crop_images_from_bbox,
    encode_image_to_base64,
    ensure_output_dir,
    extract_image_bboxes_from_page_obj,
    get_logger,
    save_model,
)

logger = get_logger(__name__)
# Set Gemini API Key (ensure this is set)
os.environ["GOOGLE_API_KEY"] = os.getenv("gemini_api_key") or ""


def process_pdf_with_llm(
    file_path: str,
    config: LLMConfig,
    response_model: type = LLMParse,
    table_handler: Optional[TableHandler] = TableHandler.html,
    denormalize_images: bool = True,
    user_question: Optional[str] = None,
    password: Optional[str] = "",
    write_to_disk: Optional[bool] = False,
    output_dir: Optional[str] = "",
    return_images: Literal["base64", "path", "none"] = "base64",
) -> List[LLMParseResult]:
    """
    Process a PDF document by sending each page as an image to an LLM dispatcher.

    Converts each page of a PDF into an image and dispatches it to a large language
    model (LLM) for structured parsing. The output includes extracted text with
    placeholders, tables, image bounding boxes, and additional metadata. Users can
    customize how image crops are returned and whether outputs should be saved to disk.

    Parameters
    ----------
    file_path : str
        Path or URL to the PDF document. Can be a local file or a remote resource.

    config : LLMConfig
        Configuration for the LLM invocation (e.g., model name, temperature, API key).

    response_model : Type[BaseModel], optional
        Pydantic model representing the expected LLM response structure.
        Defaults to `LLMParse`.

    table_handler : TableHandler, optional
        Strategy to format tables in the output. Options:
            - `TableHandler.html`: Output tables as HTML (default)
            - `TableHandler.markdown`: Output tables in Markdown

    denormalize_images : bool, optional
        Whether to convert bounding boxes from normalized coordinates (0-1 range)
        to pixel-space (absolute image dimensions). Defaults to True.

    user_question : str, optional
        Optional natural language prompt or question to guide the LLM's parsing
        or summarization for each page.

    password : str, optional
        Password for opening password-protected/encrypted PDFs. Empty by default.

    write_to_disk : bool, optional
        If True, saves output JSONs, annotated page images, and cropped regions to disk
        in a structured folder format. Defaults to False.

    output_dir : str, optional
        Base directory to save output if `write_to_disk=True`. Each page gets its
        own subdirectory under this.

    return_images : {'base64', 'path', 'none'}, optional
        Controls how cropped image regions are embedded in the return payload:
            - 'base64': Embed base64-encoded cropped images in the response (default)
            - 'path': Save images to disk and include their file paths in the response
            - 'none': Skip image crops entirely in the return payload

        If 'path' is chosen but `write_to_disk` is False, a warning is logged and
        images will not be included in the response.

    Returns
    -------
    List[LLMParseResult]
        A list of structured parsing results, one per page, each containing extracted
        content, metadata, and optional image crops depending on configuration.

    Raises
    ------
    RuntimeError
        If the PDF cannot be loaded successfully (e.g., corrupt or unreadable).
    """

    handler = PDFHandler(file_path, password=password or "")
    if handler.document is None:
        raise RuntimeError("PDF document not loaded correctly.")

    parsed_pdf = []
    total_pages = handler.total_pages
    try:
        for (
            page_number,
            image,
            (pdf_page_width, pdf_page_height),
        ) in handler.extract_screenshots():
            logger.info(f"Dispatching LLM request for page {page_number}...")
            image_bbox_guide = extract_image_bboxes_from_page_obj(
                doc=handler.document, page_number=page_number, normalize=True
            )
            try:
                llm_parse = dispatch_llm_request(
                    config=config,
                    response_model=response_model,
                    table_handler=table_handler,
                    user_question=user_question,
                    image=image,
                    image_bbox_guide=image_bbox_guide,
                )
                logger.info(f"✅ Page {page_number} response captured")
                logger.debug(f"✅ Page {page_number} response: {llm_parse}")

                if isinstance(llm_parse, str):
                    raise TypeError(
                        "Expected structured LLMParse response, got raw string."
                    )

                parsed_page = LLMParseResult(
                    config=config,
                    parse=llm_parse,
                    file_name=handler.file_name,
                    page_number=page_number,
                    total_pages=total_pages,
                    page_dimensions=(image.width, image.height),
                    pdf_page_dimensions=(pdf_page_width, pdf_page_height),
                    image_bbox_guide=image_bbox_guide,
                )

                parsed_page = postprocess_llm_response(
                    result=parsed_page,
                    denormalize_images=denormalize_images,
                )
                parsed_pdf.append(parsed_page)

                is_normalized = not denormalize_images

                annotated_image = annotate_image_with_bbox(
                    image=image,
                    image_bbox=llm_parse.image_bbox,
                    normalized=is_normalized,
                )
                cropped_images = crop_images_from_bbox(
                    image=image,
                    image_bbox=llm_parse.image_bbox,
                    normalized=is_normalized,
                )

                if write_to_disk:
                    filename = handler.file_name.replace(".", "_")
                    page_tag = f"page_{page_number:03d}"
                    output_dir_path = Path(output_dir or ".") / filename / page_tag
                    output_dir_path = ensure_output_dir(output_dir_path)
                    if output_dir_path is None:
                        logger.warning(
                            f"⚠️ Skipping disk write: could not ensure output directory"
                            f"for page {page_number}. No output directory available"
                        )
                        return []

                    if return_images in ("base64", "path"):
                        image_crops = []

                        for key, img in cropped_images.items():
                            image_entry = ImageRepresentation(
                                key=key,
                                base64=(
                                    encode_image_to_base64(img)
                                    if return_images == "base64"
                                    else None
                                ),
                                path=(
                                    str(output_dir_path / f"{key}.png")
                                    if (
                                        return_images == "path"
                                        and write_to_disk
                                        and output_dir_path
                                    )
                                    else None
                                ),
                                size=img.size,
                                format="png",
                            )
                            image_crops.append(image_entry)

                        parsed_page.image_crops = image_crops

                    output_path = output_dir_path / "response.json"
                    save_model(model=parsed_page, output_path=output_path)
                    logger.info(f"✅ Response saved at {output_path}")

                    annotated_path = output_dir_path / "annotated.png"
                    annotated_image.save(annotated_path)
                    logger.info(f"🖼️ Annotated image saved at {annotated_path}")

                    for key, cropped_img in cropped_images.items():
                        crop_path = output_dir_path / f"{key}.png"
                        cropped_img.save(crop_path)
                        logger.debug(f"🖼️ Cropped image '{key}' saved at {crop_path}")

            except Exception as e:
                logger.error(f"❌ LLM failed for page {page_number}: {e}")
                logger.error(traceback.format_exc())

    finally:
        handler.close()
        logger.info("PDF processing complete.")
    return parsed_pdf
