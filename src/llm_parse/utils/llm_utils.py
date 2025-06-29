import base64
import io
import os
from typing import List, Optional, Union

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from PIL import Image as PILImage

from ..models import LLMConfig, TableHandler
from .config_utils import load_config
from .logger import get_logger

logger = get_logger(__name__)


def supports_multimodal(provider: str, model_name: Optional[str] = None) -> bool:
    """
    Check if the given provider and model support multimodal input,
    based on YAML-defined known capabilities.

    Parameters
    ----------
    provider : str
        LLM provider name (e.g., "openai").
    model_name : str, optional
        The model name to check.

    Returns
    -------
    bool
        True if image input is likely supported; False otherwise.
    """
    provider = provider.lower()
    model_name = (model_name or "").lower()
    multimodal_support = os.path.join(
        os.path.abspath(__file__),
        os.pardir,
        os.pardir,
        os.pardir,
        os.pardir,
        "configs",
        "multimodal_models.yaml",
    )
    MULTIMODAL_MODELS = load_config(file_path=multimodal_support, dotify=True)
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
            temperature=config.temperature or 0.7,
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
    table_handler: Optional[TableHandler] = TableHandler.html,
    user_question: Optional[str] = None,
    image: Optional[Union[PILImage.Image, str]] = None,
    image_as_base64: bool = True,
) -> List[BaseMessage]:
    """
    Build prompt messages using ChatPromptTemplate for text,
    and structured content blocks for image input (if supported).

    Parameters
    ----------
    config : LLMConfig
        Contains system prompt, provider, and model name.
    table_handler : str
        Controls how extracted tables are formatted in the structured output.
        Accepted values are:
            - "html": Tables are returned as HTML strings.
            - "markdown": Tables are returned using Markdown table syntax.
        Defaults to "html".
    user_question : str, optional
        User's input prompt.
    image : Union[PIL.Image.Image, str], optional
        Image input (PIL image or URL).
    image_as_base64 : bool, default=True
        Whether to encode the PIL image as base64.

    Returns
    -------
    List[BaseMessage]
        LangChain-compatible list of messages.

    Raises
    ------
    NotImplementedError
        If image input is provided but not supported by the model.
    TypeError
        If `image` is not a valid type.
    ValueError
        If `image_as_base64` is False but image is a PIL image.
    """
    provider = config.provider
    model_name = getattr(config, "model_name", None)
    system_prompt = config.prompt
    user_input = user_question or ""
    table_format = getattr(table_handler, "value", "html")

    # Text-only messages from prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{user_input}"),
        ]
    )
    messages = prompt.format_messages(user_input=user_input, table_format=table_format)

    # Handle multimodal message
    if image:
        if not supports_multimodal(provider, model_name):
            raise NotImplementedError(
                (
                    f"Image input not supported for provider '{provider}' "
                    f"with model '{model_name}'"
                )
            )

        from typing import Dict, Union

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

        # Replace the final human message with the multimodal version
        messages[-1] = HumanMessage(content=content_blocks)

    logger.debug(f"Built prompt with image={bool(image)}: {messages}")
    return messages
