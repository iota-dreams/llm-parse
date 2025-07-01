import os

from llm_parse.models import LLMConfig, LLMParse, TableHandler
from llm_parse.parser import process_pdf_with_llm
from llm_parse.utils import get_logger, load_config

logger = get_logger("LLM_parser")
# Set Gemini API Key (ensure this is set)
os.environ["GOOGLE_API_KEY"] = os.getenv("gemini_api_key") or ""


if __name__ == "__main__":
    # example_pdf = "data/test/input/pdf/2025q1-alphabet-earnings-release.pdf"
    # example_pdf = "data/test/input/pdf/2025q1-alphabet-earnings-slides.pdf"
    example_pdf = "data/test/input/pdf/attention_is_all_you_need.pdf"
    # example_pdf = "data/test/input/pdf/empty.pdf"

    response_model = LLMParse
    table_handler = TableHandler.html
    denormalize_images = True
    user_question = None
    # user_question = "What is the summary of this page?"
    password = ""
    write_to_disk = True
    output_dir = "data/test/output/pdf"
    return_images = "path"

    parse_config = load_config("configs/prompts.yaml").parser
    config = LLMConfig(
        provider=parse_config.provider,
        model_name=parse_config.model_name,
        temperature=parse_config.get("temperature", 0.7),
        prompt=parse_config.prompt,
    )

    parsed_pdf = process_pdf_with_llm(
        file_path=example_pdf,
        config=parse_config,
        response_model=response_model,
        table_handler=table_handler,
        denormalize_images=denormalize_images,
        user_question=user_question,
        password=password,
        write_to_disk=write_to_disk,
        output_dir=output_dir,
        return_images=return_images,
    )
