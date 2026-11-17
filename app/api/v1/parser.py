import os
import shutil
from tempfile import NamedTemporaryFile
from typing import Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.schemas import PDFParseRequest
from llm_parse.models import (
    LLMConfig,
    LLMParse,
    LLMParseDocumentResponse,
    TableHandler,
)
from llm_parse.parser import process_pdf
from llm_parse.utils import get_logger, load_config_with_fallback

router = APIRouter()
logger = get_logger("LLM_API")

DEFAULT_OUTPUT_DIR = os.getenv("API_OUTPUT_DIR", "api_output")
DEFAULT_FILE = File(..., description="PDF file to parse. Must have a .pdf extension.")
DEFAULT_TABLE_HANDLER = Form(
    TableHandler.html,
    description="Table rendering strategy: 'html' or 'markdown'. Default is 'html'.",
)

# API router with versioning prefix
router = APIRouter(prefix="/api/v1", tags=["Document Parsing"])


@router.post(
    "/parse-pdf",
    response_model=LLMParseDocumentResponse,
    summary="Parse a PDF document using an LLM",
    description="""
Parses a PDF file using a Large Language Model (LLM) pipeline.

The endpoint returns structured markdown content, image metadata,
extracted tables, and other metadata. Image descriptions are optional
and can be enabled via the `enable_image_description` flag.
""",
)
async def parse_pdf_endpoint(
    file: UploadFile = DEFAULT_FILE,
    start_page: int = Form(1, description="First page to parse (1-based index)."),
    end_page: Optional[int] = Form(
        None, description="Last page to parse (inclusive, optional)."
    ),
    enable_image_description: bool = Form(
        True,
        description="Whether to generate natural language descriptions for image "
        "crops.",
    ),
    return_images: Literal["base64", "path", "none"] = Form(
        "base64",
        description="Format to return image crops in the response. "
        "'base64': Embed base64-encoded image. "
        "'path': Return file path on disk. "
        "'none': Exclude cropped images.",
    ),
    table_handler: TableHandler = DEFAULT_TABLE_HANDLER,
    write_to_disk: bool = Form(
        False,
        description="Whether to persist outputs like crops, JSON to disk.",
    ),
    output_dir: Optional[str] = Form(DEFAULT_OUTPUT_DIR),
):
    """
    Accepts a PDF and returns the parsed structured response using LLM + VLM pipeline.
    """
    if not file or not file.filename or not file.filename.lower().endswith(".pdf"):
        logger.warning("Invalid or missing PDF file.")
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file.",
        )

    logger.info(f"📄 Received PDF: {file.filename}")

    try:
        # Save uploaded file temporarily
        with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        logger.info(f"📦 Saved file to temporary path: {temp_path}")

        # Load YAML config for parser and image description models
        custom_config_path = os.getenv("PROMPT_CONFIG_PATH", "configs/prompts.yaml")
        prompt_config = load_config_with_fallback(custom_config_path)
        parser_config = LLMConfig(**dict(prompt_config.parser))
        image_config = LLMConfig(**dict(prompt_config.image_description))

        # Run LLM parser on the uploaded PDF
        logger.info("🚀 Starting PDF parsing...")
        result = process_pdf(
            file_path=temp_path,
            parser_config=parser_config,
            enable_image_description=enable_image_description,
            image_description_config=image_config,
            start_page=start_page,
            end_page=end_page,
            response_model=LLMParse,
            table_handler=table_handler,
            denormalize_images=True,
            user_question=None,
            password="",
            write_to_disk=write_to_disk,
            output_dir=output_dir,
            return_images=return_images,
            apply_document_postprocessing=True,
        )

        logger.info("✅ PDF parsing completed successfully.")

        # Clean up temp file
        os.remove(temp_path)
        logger.debug(f"🧹 Removed temp file: {temp_path}")

        # Return result as JSON
        return JSONResponse(
            content=(
                result.model_dump()
                if isinstance(result, LLMParseDocumentResponse)
                else result
            )
        )

    except Exception as e:
        logger.exception("❌ Error while processing PDF.")
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}",
        ) from e


@router.post("/json", summary="Parse PDF via JSON input")
async def parse_pdf_from_json(request: PDFParseRequest):
    """
    Accepts a JSON payload with a file path and parsing configs.
    Falls back to `configs/prompts.yaml` if parser/image_description configs
    are missing.
    """
    try:
        # Global config path override (e.g., set in Docker env or deployment)
        config_path = os.getenv("PROMPT_CONFIG_PATH", "configs/prompts.yaml")
        prompt_config = None

        # --- PARSER CONFIG ---
        if request.parser_config is not None:
            parser_config = request.parser_config
        else:
            if prompt_config is None:
                prompt_config = load_config_with_fallback(config_path)
            parser_config = LLMConfig(**prompt_config.parser.model_dump())

        # --- IMAGE DESCRIPTION CONFIG ---
        if request.enable_image_description:
            if request.image_description_config is not None:
                image_description_config = request.image_description_config
            else:
                if prompt_config is None:
                    prompt_config = load_config_with_fallback(config_path)
                image_description_config = LLMConfig(
                    **prompt_config.image_description.model_dump()
                )
        else:
            image_description_config = None

        logger.info(f"Parsing file: {request.file_path}")
        logger.info(
            f"📄 Loaded prompt config from: {config_path or 'default bundled config'}"
        )

        result = process_pdf(
            file_path=request.file_path,
            parser_config=parser_config,
            enable_image_description=request.enable_image_description,
            image_description_config=image_description_config,
            start_page=request.start_page,
            end_page=request.end_page,
            response_model=LLMParse,
            table_handler=request.table_handler,
            denormalize_images=True,
            user_question=request.user_question,
            password="",
            write_to_disk=request.write_to_disk,
            output_dir="output",
            return_images=request.return_images,
            apply_document_postprocessing=request.apply_document_postprocessing,
        )

        return JSONResponse(
            content=(
                result.model_dump()
                if isinstance(result, LLMParseDocumentResponse)
                else result
            )
        )

    except Exception as e:
        logger.exception("❌ Failed to process PDF via JSON")
        raise HTTPException(
            status_code=500, detail=f"Processing failed: {str(e)}"
        ) from e
