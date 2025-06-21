from pathlib import Path
from typing import Optional, Type, Union

import yaml

# LangChain LLM providers
from langchain.chat_models import ChatOpenAI  # GPT (OpenAI)
from langchain.schema import AIMessage, HumanMessage
from langchain_anthropic import ChatAnthropic  # Claude (Anthropic)
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI  # Gemini (Google)
from PIL import Image
from pydantic import BaseModel, ValidationError

from ..utils import get_logger

logger = get_logger(__name__)


class LLMConfig(BaseModel):
    """
    Configuration for the LLM model.
    """

    provider: str  # "gpt", "gemini", "claude"
    model_name: str
    temperature: Optional[float] = 0.7
    prompt: str  # Base system or task prompt
    image_path: Optional[Union[str, Path]] = None


def load_config(config_path: Union[str, Path]) -> LLMConfig:
    """
    Load YAML configuration file and parse into LLMConfig.

    Args:
        config_path (Union[str, Path]): Path to YAML file.

    Returns:
        LLMConfig: Parsed configuration.
    """
    logger.info(f"Loading LLM config from: {config_path}")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    config = LLMConfig(**data)
    logger.debug(f"Loaded config: {config}")
    return config


def get_llm_provider(config: LLMConfig) -> Runnable:
    """
    Instantiate the LLM provider based on config.

    Args:
        config (LLMConfig): Model configuration.

    Returns:
        Runnable: A LangChain-compatible LLM instance.

    Raises:
        ValueError: If the provider is unsupported.
    """
    logger.info(f"Initializing LLM provider: {config.provider}")
    provider = config.provider.lower()

    if provider == "gpt":
        return ChatOpenAI(model_name=config.model_name, temperature=config.temperature)
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=config.model_name, temperature=config.temperature
        )
    elif provider == "claude":
        return ChatAnthropic(
            model_name=config.model_name,
            temperature=config.temperature,
            timeout=None,
            stop=None,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")


def build_prompt(config: LLMConfig, user_question: Optional[str] = None) -> str:
    """
    Builds the full prompt using base prompt and optional user input.

    Args:
        config (LLMConfig): Configuration with base prompt.
        user_question (Optional[str]): User-provided question.

    Returns:
        str: Final prompt.
    """
    if user_question:
        logger.info("Building prompt with user question.")
    return config.prompt + (
        f"\nUser question: {user_question}" if user_question else ""
    )


def load_image(image_path: Union[str, Path]) -> Image.Image:
    """
    Load and process image from a path.

    Args:
        image_path (Union[str, Path]): File path to image.

    Returns:
        Image.Image: PIL image object.
    """
    logger.info(f"Loading image: {image_path}")
    with Image.open(image_path) as img:
        return img.convert("RGB")


def call_llm(
    config: LLMConfig,
    user_question: Optional[str] = None,
    response_model: Optional[Type[BaseModel]] = None,
) -> Union[dict, BaseModel, str]:
    """
    Call the selected LLM with a prompt (and optional image input),
    returning either raw or Pydantic-structured output.

    Args:
        config (LLMConfig): Model configuration.
        user_question (Optional[str]): Optional user input.
        response_model (Optional[Type[BaseModel]]): Pydantic model to parse response.

    Returns:
        Union[dict, BaseModel, str]: LLM response, optionally parsed.

    Raises:
        ValidationError: If parsing with Pydantic model fails.
        RuntimeError: For unsupported image handling or LLM call issues.
    """
    logger.info("Preparing to invoke LLM.")
    llm = get_llm_provider(config)
    prompt_text = build_prompt(config, user_question)
    messages = [HumanMessage(content=prompt_text)]

    if config.image_path:
        logger.info(f"Image input specified at {config.image_path}.")
        _ = load_image(config.image_path)
        raise NotImplementedError(
            "Image input support is not implemented for this provider yet."
        )

    logger.info(f"Calling model: {config.model_name}")
    try:
        response: AIMessage = llm.invoke(messages)
        logger.debug(f"Raw LLM response: {response.content}")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise RuntimeError(f"Failed to get response from LLM: {e}") from e

    if response_model:
        try:
            parsed = response_model.parse_raw(response.content)
            logger.info("Structured response parsed successfully.")
            return parsed
        except ValidationError as ve:
            logger.error(f"Failed to parse response with Pydantic model: {ve}")
            raise ve

    return response.content
