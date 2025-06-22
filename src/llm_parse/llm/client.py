from pathlib import Path
from typing import Any, Optional, Type, Union

import yaml
from langchain.chat_models import init_chat_model

# LangChain models
from langchain.schema import BaseMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from PIL import Image
from pydantic import BaseModel, ValidationError

from ..models import LLMConfig
from ..utils import get_logger

LLMOutput = Union[BaseModel, str, dict[str, Any], list[Any]]
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


def build_prompt(config: LLMConfig, user_question: Optional[str] = None) -> str:
    """
    Builds the full prompt using base prompt and optional user input.
    """
    if user_question:
        logger.info("Building prompt with user question.")
    return config.prompt + (
        f"\nUser question: {user_question}" if user_question else ""
    )


def load_image(image_path: Union[str, Path]) -> Image.Image:
    """
    Load and process image from a path.
    """
    logger.info(f"Loading image: {image_path}")
    with Image.open(image_path) as img:
        return img.convert("RGB")


def call_llm(
    config: LLMConfig,
    user_question: Optional[str] = None,
    response_model: Optional[Type[BaseModel]] = None,
) -> LLMOutput:
    logger.info("Preparing to invoke LLM.")
    llm: BaseChatModel = get_llm_provider(config)
    prompt_text = build_prompt(config, user_question)
    messages = [HumanMessage(content=prompt_text)]

    if config.image_path:
        logger.info(f"Image input specified at {config.image_path}.")
        _ = load_image(config.image_path)
        raise NotImplementedError("Image input support is not implemented yet.")

    logger.info(f"Calling model: {config.model_name}")
    try:
        if response_model:
            structured_llm = llm.with_structured_output(response_model)
            result = structured_llm.invoke(messages)
            logger.info("Structured response parsed successfully.")
            return result  # Already a BaseModel
        else:
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
