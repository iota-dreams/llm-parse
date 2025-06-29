import logging
import os
from typing import Optional

from llm_parse.file_handlers import PDFHandler
from llm_parse.llm.dispatcher import dispatch_llm_request
from llm_parse.models.models import LLMConfig, LLMParse
from llm_parse.utils import load_config

logger = logging.getLogger("LLM_parser")
# Set Gemini API Key (ensure this is set)
os.environ["GOOGLE_API_KEY"] = os.getenv("gemini_api_key") or ""


def process_pdf_with_llm(
    file_path: str,
    config: LLMConfig,
    user_question: Optional[str] = None,
    response_model: type = LLMParse,
    password: str = "",
) -> None:
    """
    Process a PDF document by sending each page as an image to an LLM dispatcher.

    Parameters:
        file_path (str): Path or URL to the PDF document.
        user_question (str): Question or prompt to ask the LLM for each page.
        config (LLMConfig): LLM configuration (provider, model, temperature, etc.).
        response_model (Type[BaseModel]): Expected structure of the LLM response.
        password (str): Optional password for encrypted PDFs.
    """
    handler = PDFHandler(file_path, password=password)

    try:
        for page_number, image in handler.extract_screenshots():
            logger.info(f"Dispatching LLM request for page {page_number}...")

            try:
                response = dispatch_llm_request(
                    config=config,
                    user_question=user_question,
                    response_model=response_model,
                    image=image,
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
