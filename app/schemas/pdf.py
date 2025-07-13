from typing import Literal, Optional

from llm_parse.models import LLMConfig, TableHandler
from pydantic import BaseModel


class PDFParseRequest(BaseModel):
    file_path: str
    start_page: int = 1
    end_page: Optional[int] = None
    enable_image_description: bool = True
    user_question: Optional[str] = None
    return_images: Literal["base64", "path", "none"] = "base64"
    table_handler: TableHandler = TableHandler.html
    write_to_disk: bool = False
    parser_config: Optional[LLMConfig] = None
    image_description_config: Optional[LLMConfig] = None
    apply_document_postprocessing: bool = True
