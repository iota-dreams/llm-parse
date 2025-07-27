import os
import sys

from llm_parse.models import LLMConfig, LLMParse, TableHandler
from llm_parse.parser import process_pdf
from llm_parse.utils import get_logger, load_config

from .cli import parse_args

logger = get_logger("LLM_parser")

if __name__ == "__main__":
    # Decide based on CLI args whether to use defaults
    cli_enabled = len(sys.argv) > 1  # True if CLI arguments are passed
    # Set Gemini API key
    os.environ["GOOGLE_API_KEY"] = os.getenv("gemini_api_key", "")

    if not cli_enabled:
        logger.info("Running in DEFAULT mode (no CLI args passed).")
        example_pdf = "data/test/input/pdf/attention_is_all_you_need.pdf"
        start_page = 3
        end_page = 6
        enable_image_description = True
        write_to_disk = True
        return_images = "path"
        output_dir = "data/test/output/pdf"
        denormalize_images = True
        user_question = None
        password = ""
        apply_document_postprocessing = True
    elif cli_enabled:
        logger.info("Running in CLI mode (arguments detected).")
        args = parse_args()
        example_pdf = args.file
        start_page = args.start_page
        end_page = args.end_page
        enable_image_description = args.enable_image_description
        write_to_disk = args.write_to_disk
        return_images = args.return_images
        output_dir = args.output_dir
        denormalize_images = args.denormalize_images
        user_question = args.question
        password = args.password
        apply_document_postprocessing = args.postprocess

    # Load prompt configs
    parser_cfg = load_config("configs/prompts.yaml").parser
    parse_config = LLMConfig(
        provider=parser_cfg.provider,
        model_name=parser_cfg.model_name,
        temperature=parser_cfg.get("temperature", 0),
        prompt=parser_cfg.prompt,
    )

    image_cfg = load_config("configs/prompts.yaml").image_description
    image_description_config = LLMConfig(
        provider=image_cfg.provider,
        model_name=image_cfg.model_name,
        temperature=image_cfg.get("temperature", 0),
        prompt=image_cfg.prompt,
    )

    # Process the PDF
    parsed_pdf = process_pdf(
        file_path=example_pdf,
        parser_config=parse_config,
        enable_image_description=enable_image_description,
        image_description_config=image_description_config,
        start_page=start_page,
        end_page=end_page,
        response_model=LLMParse,
        table_handler=TableHandler.html,
        denormalize_images=denormalize_images,
        user_question=user_question,
        password=password,
        write_to_disk=write_to_disk,
        output_dir=output_dir,
        return_images=return_images,
        apply_document_postprocessing=apply_document_postprocessing,
    )
