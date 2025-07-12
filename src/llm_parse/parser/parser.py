import traceback
from pathlib import Path
from typing import List, Literal, Optional, Union

from llm_parse.file_handlers import PDFHandler
from llm_parse.llm import dispatch_llm_request, vlm_description
from llm_parse.models import (
    ImageParseData,
    ImageRepresentation,
    LLMConfig,
    LLMParse,
    LLMParseResult,
    TableHandler,
)
from llm_parse.post_processing import (
    postprocess_document_parse_results,
    postprocess_page_parse_result,
)
from llm_parse.utils import (
    annotate_image_with_bbox,
    crop_images_from_bbox,
    encode_image_to_base64,
    ensure_output_dir,
    extract_image_bboxes_from_page_obj,
    get_logger,
    inject_pdf_hyperlinks,
    save_model,
)

from .error_handler import handle_llm_failure
from .response_builder import build_llm_parse_result

logger = get_logger(__name__)


def process_pdf_with_llm(
    file_path: str,
    parser_config: LLMConfig,
    enable_image_description: bool = False,
    image_description_config: Optional[LLMConfig] = None,
    start_page: int = 1,
    end_page: Optional[int] = None,
    response_model: type = LLMParse,
    table_handler: Optional[TableHandler] = TableHandler.html,
    denormalize_images: bool = True,
    user_question: Optional[str] = None,
    password: Optional[str] = "",
    write_to_disk: Optional[bool] = False,
    output_dir: Optional[str] = "",
    return_images: Literal["base64", "path", "none"] = "base64",
    apply_document_postprocessing: bool = True,
    **post_process_kwargs,
) -> Union[List[LLMParseResult], dict]:
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

    parser_config : LLMConfig
        Configuration for the LLM invocation (e.g., model name, temperature)
        for parser.

    enable_image_description : bool, default=False
        If True, each cropped image (based on LLM-provided bounding boxes) will be
        passed to a visual-language model (VLM) to generate a natural language
        description. The generated descriptions will be stored in
        `parsed_page.image_description` as a dictionary mapping image keys
        (e.g., "image_1") to structured outputs.

        This is useful for tasks that require semantic understanding of visual
        elements (e.g., document summarization, accessibility, indexing).

    image_description_config : Optional[LLMConfig]
        Configuration for the visual-language model used in image description.
        Only used if `enable_image_description` is True.

    start_page (int):
        1-based index of first page to process.

    end_page (Optional[int]):
        1-based index of last page to process (inclusive).

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

    apply_document_postprocessing : bool, optional
        Whether to apply post-processing to the raw LLM parse results before returning.
        If True (default), the results are transformed into a RAG-friendly response
        format. If False, the raw parsed results are returned as-is.

    post_process_kwargs : dict, optional
        Additional keyword arguments passed to the post-processing function.
        Useful for controlling post-processing behavior like preference for file paths
        or other future options. If no additional options are needed, this can be
        omitted.

    Returns
    -------
    Union[List[LLMParseResult], dict]
        - Raw page-level parse results (if post_process=False)
        - Final RAG-friendly structure (if post_process=True)

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
        ) in handler.extract_screenshots(start_page=start_page, end_page=end_page):
            logger.info(f"Dispatching LLM request for page {page_number}...")
            image_bbox_guide = extract_image_bboxes_from_page_obj(
                doc=handler.document, page_number=page_number, normalize=True
            )
            try:
                table_format = getattr(table_handler, "value", "html")

                llm_parse = dispatch_llm_request(
                    config=parser_config,
                    response_model=response_model,
                    user_question=user_question,
                    image=image,
                    table_format=table_format,
                    image_bbox_guide=image_bbox_guide,
                )

                logger.info(f"✅ Page {page_number} response captured")
                logger.debug(f"✅ Page {page_number} response: {llm_parse}")

                if isinstance(llm_parse, str):
                    raise TypeError(
                        "Expected structured LLMParse response, got raw string."
                    )

                # Step 1: Extract and inject hyperlinks
                parsed_page, hyperlink_uris = inject_pdf_hyperlinks(
                    llm_parse=llm_parse,
                    page_obj=handler.document[page_number - 1],
                    relative_hyperlink_extract=True,
                )

                # Step 2: Annotate and crop image using bounding boxes
                # We are prompting LLM to give normalized bboxes. So, this can be
                # set to `True`
                is_normalized = True

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

                # Step 3: Optionally describe cropped image regions using VLM
                image_descriptions = None
                if (
                    enable_image_description
                    and cropped_images
                    and image_description_config
                ):
                    prompt = image_description_config.prompt
                    image_descriptions = vlm_description(
                        images=cropped_images,
                        config=image_description_config,
                        prompt=prompt,
                    )

                # Step 4: Finalize parsed page using build_llm_parse_result
                parsed_page = build_llm_parse_result(
                    llm_parse=llm_parse,
                    parser_config=parser_config,
                    file_name=handler.file_name,
                    page_number=page_number,
                    total_pages=total_pages,
                    image=image,
                    pdf_page_dimensions=(pdf_page_width, pdf_page_height),
                    hyperlink_guide=hyperlink_uris,
                    image_data=ImageParseData(
                        bbox_guide=image_bbox_guide,
                        descriptions=image_descriptions,
                        description_config=image_description_config,
                    ),
                )

                # Step 5: Page-level postprocessing (e.g., denormalization)
                parsed_page = postprocess_page_parse_result(
                    result=parsed_page,
                    denormalize_images=denormalize_images,
                )

                # Step 6: Append to result list
                parsed_pdf.append(parsed_page)

                filename = handler.file_name.replace(".", "_")

                # Build image crops
                image_crops = []

                if return_images in ("base64", "path"):
                    for key, img in cropped_images.items():
                        image_entry = ImageRepresentation(
                            key=key,
                            base64=(
                                encode_image_to_base64(img)
                                if return_images == "base64"
                                else None
                            ),
                            path=(
                                str(
                                    Path(output_dir or ".")
                                    / filename
                                    / f"page_{page_number:03d}"
                                    / f"{key}.png"
                                )
                                if return_images == "path"
                                else None
                            ),
                            size=img.size,
                            format="png",
                        )
                        image_crops.append(image_entry)

                if parsed_page.image_data is None:
                    parsed_page.image_data = ImageParseData()

                parsed_page.image_data.crops = image_crops

                # This block ONLY handles disk writing
                if write_to_disk:
                    page_tag = f"page_{page_number:03d}"
                    output_dir_path = Path(output_dir or ".") / filename / page_tag
                    output_dir_path = ensure_output_dir(output_dir_path)
                    if output_dir_path is None:
                        logger.warning(
                            f"⚠️ Skipping disk write: could not ensure output directory "
                            f"for page {page_number}. No output directory available"
                        )
                    else:
                        output_path = output_dir_path / "response.json"
                        save_model(model=parsed_page, output_path=output_path)
                        logger.info(f"✅ Response saved at {output_path}")

                        annotated_path = output_dir_path / "annotated.png"
                        annotated_image.save(annotated_path)
                        logger.info(f"🖼️ Annotated image saved at {annotated_path}")

                        for key, cropped_img in cropped_images.items():
                            crop_path = output_dir_path / f"{key}.png"
                            cropped_img.save(crop_path)
                            logger.debug(
                                f"🖼️ Cropped image '{key}' saved at {crop_path}"
                            )

                logger.info(
                    f"{'--'*50}\nParsing completed for the file:page {filename}:"
                    f"{page_number}"
                )

            except Exception as e:
                logger.error(f"❌ LLM failed for page {page_number}: {e}")
                logger.error(traceback.format_exc())
                fallback = handle_llm_failure(
                    file_name=handler.file_name,
                    page_number=page_number,
                    total_pages=total_pages,
                    parser_config=parser_config,
                    image=image,
                    pdf_page_dimensions=(pdf_page_width, pdf_page_height),
                    image_bbox_guide=image_bbox_guide,
                    output_dir=output_dir,
                    write_to_disk=(
                        write_to_disk if write_to_disk is not None else False
                    ),
                    return_images=return_images,
                    error=e,
                )
                parsed_pdf.append(fallback)

    finally:
        handler.close()
        logger.info("PDF processing complete.")
    if apply_document_postprocessing:
        logger.info("Applying document-level post-processing to all parsed pages...")
        post_process_kwargs.setdefault("start_page", start_page)
        post_process_kwargs.setdefault("end_page", end_page or total_pages)

        processed_output = postprocess_document_parse_results(
            parsed_pdf, **post_process_kwargs
        )
        logger.info("Returning final processed document parse results.")

        if write_to_disk:
            output_pdf_path = Path(output_dir or ".") / filename / "parsed_output.json"
            # Ensure the parent directory exists
            output_dir_path = ensure_output_dir(output_pdf_path.parent)
            if output_dir_path is not None:
                save_model(processed_output, output_pdf_path)
            else:
                logger.warning("❌ Skipping save: Unable to ensure output directory.")
        return processed_output
    else:
        logger.info("Returning raw parsed results without post-processing.")
        return parsed_pdf
