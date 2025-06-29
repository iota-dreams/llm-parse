import os
from pathlib import Path
from typing import Optional

from llm_parse.file_handlers import PDFHandler
from llm_parse.llm.dispatcher import dispatch_llm_request
from llm_parse.models import LLMConfig, LLMParse, TableHandler
from llm_parse.utils import (
    ensure_output_dir,
    extract_image_bboxes_from_page_obj,
    get_logger,
    save_model,
)

logger = get_logger("LLM_parser")
# Set Gemini API Key (ensure this is set)
os.environ["GOOGLE_API_KEY"] = os.getenv("gemini_api_key") or ""


def process_pdf_with_llm(
    file_path: str,
    config: LLMConfig,
    response_model: type = LLMParse,
    table_handler: Optional[TableHandler] = TableHandler.html,
    user_question: Optional[str] = None,
    password: Optional[str] = "",
    write_to_disk: Optional[bool] = False,
    output_dir: Optional[str] = "",
) -> None:
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

    try:
        for page_number, image in handler.extract_screenshots():
            logger.info(f"Dispatching LLM request for page {page_number}...")
            image_bbox_guide = extract_image_bboxes_from_page_obj(
                doc=handler.document, page_number=page_number
            )
            try:
                response = dispatch_llm_request(
                    config=config,
                    response_model=response_model,
                    table_handler=table_handler,
                    user_question=user_question,
                    image=image,
                    image_bbox_guide=image_bbox_guide,
                )
                logger.info(f"✅ Page {page_number} response captured")
                logger.debug(f"✅ Page {page_number} response: {response}")
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
                        model=response,
                        output_path=output_path,
                    )
                    logger.info(f"✅ Response saved in {output_path}")

            except Exception as e:
                logger.error(f"❌ LLM failed for page {page_number}: {e}")

    finally:
        handler.close()
        logger.info("PDF processing complete.")
