import logging
import os
from typing import Optional

from llm_parse.file_handlers import PDFHandler
from llm_parse.llm.dispatcher import dispatch_llm_request
from llm_parse.models import LLMConfig, LLMParse, TableHandler
from llm_parse.utils import extract_image_bboxes_from_page_obj, load_config

logger = logging.getLogger("LLM_parser")
# Set Gemini API Key (ensure this is set)
os.environ["GOOGLE_API_KEY"] = os.getenv("gemini_api_key") or ""


def process_pdf_with_llm(
    file_path: str,
    config: LLMConfig,
    response_model: type = LLMParse,
    table_handler: Optional[TableHandler] = TableHandler.html,
    user_question: Optional[str] = None,
    password: str = "",
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
    handler = PDFHandler(file_path, password=password)

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
                logger.info(f"✅ Page {page_number} response: {response}")

            except Exception as e:
                logger.error(f"❌ LLM failed for page {page_number}: {e}")

    finally:
        handler.close()
        logger.info("PDF processing complete.")


if __name__ == "__main__":
    example_pdf = "data/test/pdf/2025q1-alphabet-earnings-release.pdf"
    example_question = "What is the summary of this page?"

    parse_config = load_config("configs/prompts.yaml").parser
    config = LLMConfig(
        provider=parse_config.provider,
        model_name=parse_config.model_name,
        temperature=parse_config.get("temperature", 0.7),
        prompt=parse_config.prompt,
    )

    process_pdf_with_llm(
        file_path=example_pdf,
        config=parse_config,
    )
