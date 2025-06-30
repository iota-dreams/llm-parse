import os
from pathlib import Path
from typing import List, Optional

from llm_parse.file_handlers import PDFHandler
from llm_parse.llm.dispatcher import dispatch_llm_request
from llm_parse.models import LLMConfig, LLMParse, LLMParseResult, TableHandler
from llm_parse.post_processing import postprocess_llm_response
from llm_parse.utils import (
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
) -> List[LLMParseResult]:
    """
    Process a PDF document by sending each page as an image to an LLM dispatcher.

    Each page of the PDF is converted to an image and sent to a language model for
    parsing and structured response generation. Tables, text, and visual elements
    can be extracted based on the response model and formatting preferences.

    Parameters
    ----------
    file_path : str
        Path or URL to the PDF document. Can be a local file system path or a remote
        link.

    user_question : str
        Question or instruction to pass to the LLM for each page. This guides the
        parsing or summarization behavior of the model.

    response_model : Type[BaseModel]
        Pydantic model class defining the expected structure of the LLM response.
        The model should match the structure used in parsing logic.

    table_handler : str
        Controls how extracted tables are formatted in the structured output.
        Accepted values are:
            - "html": Tables are returned as HTML strings.
            - "markdown": Tables are returned using Markdown table syntax.
        Defaults to "html".

    denormalize_images : bool, optional
        Whether to convert image bounding boxes from normalized to absolute coordinates.

    config : LLMConfig
        Configuration object containing LLM provider settings such as model name,
        temperature, API key, and other generation parameters.

    password : str, optional
        Password for opening encrypted PDFs. If not provided, encrypted PDFs will
        fail to open unless accessible without a password.

    Raises
    ------
    RuntimeError
        If the document loading fails or is None.
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
            (page_width, page_height),
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
                # To handle when llm_parse is an unknown unhandled error when we
                # manually asked to return LLM response could not be parsed or matched
                # expected format
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
                    page_dimensions=(page_width, page_height),
                    image_bbox_guide=image_bbox_guide,
                )

                parsed_page.page_dimensions = (page_width, page_height)
                parsed_page = postprocess_llm_response(
                    result=parsed_page, denormalize_images=denormalize_images
                )
                parsed_pdf.append(parsed_page)
                if write_to_disk:
                    safe_output_dir = output_dir or ""
                    filename = handler.file_name.replace(".", "_")
                    output_filename = f"page_{page_number}.json"
                    if safe_output_dir:
                        output_dir_path = Path(safe_output_dir) / filename
                        output_path = output_dir_path / output_filename
                    else:
                        output_path = Path(filename)
                    safe_output_dir = ensure_output_dir(output_dir_path)

                    save_model(
                        model=parsed_page,
                        output_path=output_path,
                    )
                    logger.info(f"✅ Response saved in {output_path}")

            except Exception as e:
                logger.error(f"❌ LLM failed for page {page_number}: {e}")

    finally:
        handler.close()
        logger.info("PDF processing complete.")
    return parsed_pdf
