import os

from llm_parse.models import LLMConfig, LLMParse, TableHandler
from llm_parse.parser import process_pdf_with_llm
from llm_parse.utils import get_logger, load_config

logger = get_logger("LLM_parser")

if __name__ == "__main__":
    # Set Gemini API Key (ensure this is set)
    os.environ["GOOGLE_API_KEY"] = os.getenv("gemini_api_key") or ""

    # example_pdf = "data/test/input/pdf/2025q1-alphabet-earnings-release.pdf"
    example_pdf = "data/test/input/pdf/2025q1-alphabet-earnings-slides.pdf"
    # example_pdf = "data/test/input/pdf/attention_is_all_you_need.pdf"
    # example_pdf = "data/test/input/pdf/empty.pdf"
    enable_image_description = True
    start_page = 5
    end_page = None
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
    parse_config = LLMConfig(
        provider=parse_config.provider,
        model_name=parse_config.model_name,
        temperature=parse_config.get("temperature", 0.7),
        prompt=parse_config.prompt,
    )
    image_description_config = load_config("configs/prompts.yaml").image_description
    image_description_config = LLMConfig(
        provider=image_description_config.provider,
        model_name=image_description_config.model_name,
        temperature=image_description_config.get("temperature", 0.7),
        prompt=image_description_config.prompt,
    )

    parsed_pdf = process_pdf_with_llm(
        file_path=example_pdf,
        parser_config=parse_config,
        enable_image_description=enable_image_description,
        image_description_config=image_description_config,
        start_page=start_page,
        end_page=end_page,
        response_model=response_model,
        table_handler=table_handler,
        denormalize_images=denormalize_images,
        user_question=user_question,
        password=password,
        write_to_disk=write_to_disk,
        output_dir=output_dir,
        return_images=return_images,
    )
