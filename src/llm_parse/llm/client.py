import base64
import io
from pathlib import Path
from typing import List, Optional, Type, Union

import yaml
from langchain.chat_models import init_chat_model

# LangChain models
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from PIL import Image as PILImage
from pydantic import BaseModel, ValidationError

from ..models import LLMConfig
from ..utils import get_logger, supports_multimodal

LLMOutput = Union[str, dict, list, BaseModel]
logger = get_logger(__name__)


def load_config(config_path: Union[str, Path]) -> LLMConfig:
    """
    Load YAML configuration file and parse into LLMConfig.
    """
    logger.info(f"Loading LLM config from: {config_path}")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    config = LLMConfig(**data)
    logger.debug(f"Loaded config: {config}")
    return config


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

    # Text-only messages from prompt template
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{user_input}")]
    )
    messages = prompt.format_messages(user_input=user_input)

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


def load_image(image_path: Union[str, Path]) -> PILImage.Image:
    """
    Load and process image from a path.
    """
    logger.info(f"Loading image: {image_path}")
    with PILImage.open(image_path) as img:
        return img.convert("RGB")


def call_llm(
    config: LLMConfig,
    user_question: Optional[str] = None,
    response_model: Optional[Type[BaseModel]] = None,
    image: Optional[PILImage.Image] = None,
) -> LLMOutput:
    """
    Calls an LLM using the provided config and question, with optional image and
    structured response.

    Parameters
    ----------
    config : LLMConfig
        Configuration containing model, provider, prompt, etc.
    user_question : str, optional
        The user's question or prompt.
    response_model : Type[BaseModel], optional
        A Pydantic model to parse the response into structured format.
    image : PIL.Image.Image, optional
        Optional image input. If not provided, falls back to `config.image_path`.

    Returns
    -------
    Union[str, dict, list, BaseModel]
        Raw string or structured result from the LLM.

    Raises
    ------
    ValidationError
        If structured parsing fails.
    RuntimeError
        If LLM invocation fails.
    """
    logger.info("Preparing to invoke LLM.")

    # Use provided image or load from path
    if image is None and config.image_path:
        logger.info(f"Loading image from path: {config.image_path}")
        image = load_image(config.image_path)

    # Initialize the LLM instance
    llm: BaseChatModel = init_chat_model(
        model=config.model_name,
        model_provider=config.provider,
        temperature=config.temperature or 0.7,
        timeout=getattr(config, "timeout", None),
    )

    # Build prompt with optional image support
    messages = build_prompt(config, user_question, image=image)

    logger.info(f"Calling model: {config.model_name}")
    try:
        if response_model:
            structured_llm = llm.with_structured_output(response_model)
            result = structured_llm.invoke(messages)
            logger.info("Structured response parsed successfully.")
            return result

        response: BaseMessage = llm.invoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, (str, dict, list)):
            return content
        return str(content)

    except ValidationError as ve:
        logger.error(f"Failed to parse response with Pydantic model: {ve}")
        raise
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise RuntimeError(f"Failed to get response from LLM: {e}") from e
