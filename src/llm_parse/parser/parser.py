import io
import traceback
from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple, Union

import fitz  # PyMuPDF
from PIL import Image

from llm_parse.file_handlers import PDFHandler
from llm_parse.llm import dispatch_llm_request, vlm_description
from llm_parse.models import (
    ImageParseData,
    ImageRepresentation,
    LLMConfig,
    LLMParse,
    LLMParseDocumentResponse,
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


def process_pdf(
    file_path: str,
    parser_config: LLMConfig,
    enable_image_description: bool = False,
    image_description_config: Optional[LLMConfig] = None,
    start_page: int = 1,
    end_page: Optional[int] = None,
    response_model: type = LLMParse,
    table_handler: TableHandler = TableHandler.html,
    denormalize_images: bool = True,
    user_question: Optional[str] = None,
    password: Optional[str] = "",
    write_to_disk: bool = False,
    output_dir: Optional[str] = None,
    return_images: Literal["base64", "path", "none"] = "base64",
    apply_document_postprocessing: bool = True,
    **post_process_kwargs: Any,
) -> Union[List[LLMParseResult], LLMParseDocumentResponse]:
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

    post_process_kwargs : Dict[str, Any], optional
        Additional keyword arguments passed to `postprocess_document_parse_results`.

        Supported keys:
            - prefer_file_path (bool, default=True): If True, image crops in the final
              output will prefer file paths over base64-encoded strings.
            - start_page (int, optional): First page index used during parsing.
            Automatically inferred if not provided.
            - end_page (int, optional): Last page index used during parsing.
            Automatically inferred if not provided.

    Returns
    -------
    Union[List[LLMParseResult], LLMParseDocumentResponse]
        - List of page-level results (if apply_document_postprocessing=False)
        - Combined and enriched document-level output
        (if apply_document_postprocessing=True)

    Raises
    ------
    RuntimeError
        If the PDF cannot be loaded successfully (e.g., corrupt or unreadable).
    """
    if not output_dir:
        output_dir = "."

    handler = PDFHandler(file_path, password=password or "")
    if handler.document is None:
        raise RuntimeError("PDF document not loaded correctly.")

    parsed_pdf = []
    total_pages = handler.total_pages
    filename = handler.file_name.replace(".", "_")

    try:
        logger.info(
            f"Starting PDF parsing from page {start_page} to "
            f"{end_page or handler.total_pages}"
        )

        for (
            page_number,
            image,
            (pdf_page_width, pdf_page_height),
        ) in handler.extract_screenshots(start_page=start_page, end_page=end_page):
            page_obj = handler.document.load_page(page_number - 1)
            parsed_page = parse_page(
                page_obj=page_obj,
                parser_config=parser_config,
                response_model=response_model,
                table_handler=table_handler,
                user_question=user_question,
                enable_image_description=enable_image_description,
                image_description_config=image_description_config,
                denormalize_images=denormalize_images,
                return_images=return_images,
                write_to_disk=write_to_disk,
                output_dir=output_dir,
                page_number=page_number,
                total_pages=total_pages,
                file_name=filename,
                image=image,
                pdf_page_dimensions=(pdf_page_width, pdf_page_height),
            )
            parsed_pdf.append(parsed_page)

    finally:
        handler.close()
        logger.info("PDF processing complete.")
    if apply_document_postprocessing:
        logger.info("Applying document-level post-processing to all parsed pages...")
        post_process_kwargs.setdefault("start_page", start_page)
        post_process_kwargs.setdefault("end_page", end_page or total_pages)

        processed_data = postprocess_document_parse_results(
            parsed_pdf, **post_process_kwargs
        )
        logger.info("Returning final processed document parse results.")

        # Wrap the output in the response model if it's not already
        document_response = LLMParseDocumentResponse(**processed_data)

        if write_to_disk:
            output_pdf_path = Path(output_dir or ".") / filename / "parsed_output.json"
            output_dir_path = ensure_output_dir(output_pdf_path.parent)
            if output_dir_path is not None:
                save_model(document_response, output_pdf_path)
            else:
                logger.warning("❌ Skipping save: Unable to ensure output directory.")

        return document_response
    else:
        logger.info("Returning raw parsed results without post-processing.")
        return parsed_pdf


def parse_page(
    *,
    page_obj: fitz.Page,
    parser_config: LLMConfig,
    response_model: type = LLMParse,
    table_handler: Optional[TableHandler] = TableHandler.html,
    user_question: Optional[str] = None,
    enable_image_description: bool = False,
    image_description_config: Optional[LLMConfig] = None,
    denormalize_images: bool = True,
    return_images: Literal["base64", "path", "none"] = "base64",
    write_to_disk: bool = False,
    output_dir: Optional[str] = None,
    page_number: int = 1,
    total_pages: Optional[int] = None,
    file_name: Optional[str] = "document",
    image: Optional[Image.Image] = None,
    pdf_page_dimensions: Optional[Tuple[float, float]] = None,
) -> LLMParseResult:
    """
    Parses a single PDF page using the LLM pipeline and returns a structured result.

    Supports both:
    - Standalone parsing: Just pass `page_obj`; the rest is inferred.
    - Batched parsing (via `process_pdf`): `image`, `file_name`, etc. are passed in.

    Parameters
    ----------
    page_obj : fitz.Page
        Required. The PDF page object to parse.

    parser_config : Optional[LLMConfig]
        Required if calling LLMs. Model settings for LLM dispatcher.

    response_model : type
        Pydantic model to decode LLM response. Defaults to LLMParse.

    table_handler : Optional[TableHandler]
        How to render tables (e.g., 'html' or 'markdown').

    user_question : Optional[str]
        Optional user prompt to guide LLM parsing.

    enable_image_description : bool
        If True, cropped regions are described using a vision-language model (VLM).

    image_description_config : Optional[LLMConfig]
        LLMConfig for the image captioning VLM.

    denormalize_images : bool
        Convert normalized bounding boxes to pixel-space if True.

    return_images : {"base64", "path", "none"}
        Controls how image crops are embedded.

    write_to_disk : bool
        Save annotated/cropped images and JSON output to disk.

    output_dir : Optional[str]
        Base directory for file outputs.

    page_number : int, default=1
        1-based page number. Defaults to 1 in standalone use.

    total_pages : Optional[int]
        Total number of pages in the document. Defaults to 1 if not passed.

    file_name : Optional[str]
        File name for metadata and output. Defaults to "document".

    image : Optional[Image.Image]
        Pre-rendered image of the page. If not provided, it's rendered from `page_obj`.

    pdf_page_dimensions : Optional[Tuple[float, float]]
        Dimensions in PDF space. If not provided, it's extracted from `page_obj`.

    Returns
    -------
    LLMParseResult
        Structured parse output with metadata and optionally image data.
    """
    if image is None:
        pix = page_obj.get_pixmap(dpi=300)  # type: ignore[attr-defined]
        image = Image.open(io.BytesIO(pix.tobytes("png")))

    if pdf_page_dimensions is None:
        pdf_page_dimensions = (page_obj.rect.width, page_obj.rect.height)

    if total_pages is None:
        total_pages = 1

    file_name = file_name or "document"

    assert page_obj.parent is not None, "Expected non-null parent document for page_obj"
    image_bbox_guide = extract_image_bboxes_from_page_obj(
        doc=page_obj.parent,
        page_number=page_number,
        normalize=True,
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
            raise TypeError("Expected structured LLMParse response, got raw string.")

        parsed_page, hyperlink_uris = inject_pdf_hyperlinks(
            llm_parse=llm_parse,
            page_obj=page_obj,
            relative_hyperlink_extract=True,
        )

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

        image_descriptions = None
        if enable_image_description and cropped_images and image_description_config:
            prompt = image_description_config.prompt
            image_descriptions = vlm_description(
                images=cropped_images,
                config=image_description_config,
                prompt=prompt,
            )

        parsed_page = build_llm_parse_result(
            llm_parse=llm_parse,
            parser_config=parser_config,
            file_name=file_name,
            page_number=page_number,
            total_pages=total_pages,
            image=image,
            pdf_page_dimensions=pdf_page_dimensions,
            hyperlink_guide=hyperlink_uris,
            image_data=ImageParseData(
                bbox_guide=image_bbox_guide,
                descriptions=image_descriptions,
                description_config=image_description_config,
            ),
        )

        parsed_page = postprocess_page_parse_result(
            result=parsed_page,
            denormalize_images=denormalize_images,
        )

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
                            / file_name.replace(".", "_")
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

        if write_to_disk:
            output_base = Path(output_dir or ".") / file_name.replace(".", "_")
            output_dir_path = ensure_output_dir(output_base / f"page_{page_number:03d}")
            if output_dir_path is not None:
                save_model(parsed_page, output_dir_path / "response.json")
                annotated_image.save(output_dir_path / "annotated.png")
                for key, cropped_img in cropped_images.items():
                    cropped_img.save(output_dir_path / f"{key}.png")
            else:
                logger.warning("⚠️ Skipping disk write: Unable to ensure output dir.")

        logger.info(f"✅ Completed parsing for {file_name}:page {page_number}")
        logger.info(
            f"✅ Completed parsing for file:page {file_name}:"
            f"{page_number} {'--'*50}\n"
        )
        return parsed_page

    except Exception as e:
        logger.error(f"❌ LLM failed for page {page_number}: {e}")
        logger.error(traceback.format_exc())
        return handle_llm_failure(
            file_name=file_name,
            page_number=page_number,
            total_pages=total_pages,
            parser_config=parser_config,
            image=image,
            pdf_page_dimensions=pdf_page_dimensions,
            image_bbox_guide=image_bbox_guide,
            output_dir=output_dir,
            write_to_disk=write_to_disk,
            return_images=return_images,
            error=e,
        )
