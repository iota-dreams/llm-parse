import base64
import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from PIL import Image as PILImage

from ..models import LLMConfig
from .config_utils import load_config_with_fallback
from .logger import get_logger

logger = get_logger(__name__)


def supports_multimodal(provider: str, model_name: Optional[str] = None) -> bool:
    """
    Check if the given provider and model support multimodal input,
    based on YAML-defined known capabilities.

    Uses CONFIG_ROOT environment variable to locate YAML files.
    """
    provider = provider.lower()
    model_name = (model_name or "").lower()

    # Resolve config root from environment or fallback to ./configs
    env_root = os.getenv("CONFIG_ROOT")
    default_root = Path(__file__).resolve().parents[3] / "configs"
    config_root = Path(env_root) if env_root else default_root

    config_path = config_root / "multimodal_models.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Multimodal config not found: {config_path}")

    logger.info(f"Loading multimodal config from: {config_path}")
    MULTIMODAL_MODELS = load_config_with_fallback(
        custom_path=str(config_path), dotify=True
    )
    supported_models = MULTIMODAL_MODELS.get(provider, [])
    return any(substr in model_name for substr in supported_models)


def get_llm_provider(config: LLMConfig) -> BaseChatModel:
    """
    Dispatcher to get the appropriate LLM based on provider.
    """
    provider = config.provider.lower()
    logger.info(f"Initializing LLM provider: {provider}")

    try:
        llm = init_chat_model(
            model=config.model_name,
            model_provider=provider,
            temperature=config.temperature or 0.3,
            timeout=getattr(config, "timeout", None),
        )
        if not isinstance(llm, BaseChatModel):
            raise TypeError("The initialized LLM is not a BaseChatModel instance.")
        return llm
    except Exception as e:
        logger.error(f"Error while initializing the LLM: {e}")
        value_error = (
            f"Unsupported LLM provider: {config.provider} or error while "
            "initializing the LLM model"
        )
        raise ValueError(value_error) from e


def build_prompt(
    config: LLMConfig,
    user_question: Optional[str] = None,
    image: Optional[Union[PILImage.Image, str]] = None,
    image_as_base64: bool = True,
    **kwargs: Any,
) -> List[BaseMessage]:
    """
    Builds a list of prompt messages for the LLM, optionally including image and
    dynamic placeholders for formatting (e.g., table_handler, image_bbox_guide, etc.).

    Parameters
    ----------
    config : LLMConfig
        LLM system config containing model, provider, prompt, etc.
    user_question : str, optional
        User-provided query or instruction.
    image : PIL.Image.Image or str, optional
        Optional image input. Can be a PIL image or URL string.
    image_as_base64 : bool, default=True
        Whether to base64-encode the image.
    **kwargs : dict
        Dynamic placeholders to pass to the prompt formatter.

    Returns
    -------
    List[BaseMessage]
        LangChain-compatible list of messages.

    Raises
    ------
    NotImplementedError
        If model doesn't support image input.
    TypeError
        If invalid image type is passed.
    ValueError
        If base64 encoding is disabled but a PIL image is passed.
    """
    provider = config.provider
    model_name = getattr(config, "model_name", None)
    system_prompt = config.prompt
    user_input = user_question or ""

    # Build base prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{user_input}"),
        ]
    )

    # Format messages with dynamic placeholders
    messages = prompt.format_messages(
        user_input=user_input,
        **kwargs,
    )

    # Handle multimodal message
    if image:
        if not supports_multimodal(provider, model_name):
            raise NotImplementedError(
                f"Image input not supported for provider '{provider}' with model"
                f"'{model_name}'"
            )

        content_blocks: List[Union[str, Dict[str, str]]] = [
            {"type": "text", "text": user_input}
        ]

        if isinstance(image, str):
            content_blocks.append({"type": "image", "source_type": "url", "url": image})
        elif isinstance(image, PILImage.Image):
            if not image_as_base64:
                raise ValueError("Only base64 encoding is supported for PIL.Image.")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            content_blocks.append(
                {
                    "type": "image",
                    "source_type": "base64",
                    "data": img_b64,
                    "mime_type": "image/png",
                }
            )
        else:
            raise TypeError("Image must be a PIL.Image.Image or a URL string.")

        messages[-1] = HumanMessage(content=content_blocks)

    logger.debug(f"Built prompt with image={bool(image)}: {messages}")
    return messages
