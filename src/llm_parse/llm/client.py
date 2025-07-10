from typing import Any, Dict, Optional, Type, Union

from langchain.chat_models import init_chat_model

# LangChain models
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from PIL import Image as PILImage
from pydantic import BaseModel, ValidationError

from ..models import LLMConfig
from ..utils import build_prompt, get_logger

LLMOutput = Union[str, dict, list, BaseModel]
logger = get_logger(__name__)


def call_llm(
    config: LLMConfig,
    response_model: Optional[Type[BaseModel]] = None,
    prompt_context: Optional[Dict[str, Any]] = None,
    user_question: Optional[str] = None,
    image: Optional[PILImage.Image] = None,
) -> LLMOutput:
    """
    Calls an LLM using the provided config and user input, with optional image and
    structured response model. Accepts a flexible prompt_context for formatting.
    Attempts to include safety_settings, but gracefully ignores them if they are invalid
    or rejected by the provider.

    Parameters
    ----------
    config : LLMConfig
        Configuration containing model name, provider, and system prompt.
    response_model : Type[BaseModel], optional
        Pydantic model for structured response parsing.
    prompt_context : dict, optional
        Placeholder values (e.g., table_handler, image_bbox_guide, etc.) for prompt.
    user_question : str, optional
        The user's question or prompt.
    image : PIL.Image.Image, optional
        Optional image to be sent to the LLM.

    Returns
    -------
    Union[str, dict, list, BaseModel]
        Raw or structured output from the LLM.

    Raises
    ------
    ValidationError
        If Pydantic parsing fails.
    RuntimeError
        If LLM invocation fails.
    """
    logger.info("Preparing to invoke LLM.")

    if prompt_context is None:
        prompt_context = {}

    model_kwargs = {}
    raw_safety_settings = getattr(config, "safety_settings", None)

    if isinstance(raw_safety_settings, list):
        if all(isinstance(x, dict) for x in raw_safety_settings):
            model_kwargs["safety_settings"] = raw_safety_settings
        elif raw_safety_settings:  # non-empty but contains bad elements
            logger.warning(
                "Ignoring malformed safety_settings (must be list of dicts)."
            )
    elif raw_safety_settings is not None:
        logger.warning("Ignoring safety_settings: must be a list.")

    try:
        # Initialize LLM backend
        llm: BaseChatModel = init_chat_model(
            model=config.model_name,
            model_provider=config.provider,
            temperature=config.temperature or 0.7,
            timeout=getattr(config, "timeout", None),
            model_kwargs=model_kwargs,
        )

        # Compose prompt with placeholders
        messages = build_prompt(
            config=config,
            user_question=user_question,
            image=image,
            **prompt_context,
        )

        logger.info(f"Calling model: {config.model_name}")

        if response_model:
            structured_llm = llm.with_structured_output(
                response_model, include_raw=True
            )
            result = structured_llm.invoke(messages)
            logger.debug(f"Structured LLM output: {result}")
            return result

        # Fallback: no response model
        response: BaseMessage = llm.invoke(messages)
        content = getattr(response, "content", response)

        if isinstance(content, (str, dict, list)):
            logger.debug(f"Unstructured LLM output: {content}")
            return content

        logger.warning(
            f"Unexpected LLM response type: {type(content)}. Converting to string."
        )
        return str(content)

    except ValidationError as ve:
        logger.error(f"Failed to parse response with Pydantic model: {ve}")
        raise
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise RuntimeError(f"Failed to get response from LLM: {e}") from e
