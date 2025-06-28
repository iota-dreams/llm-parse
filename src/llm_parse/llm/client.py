from typing import Optional, Type, Union

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
            structured_llm = llm.with_structured_output(
                response_model, include_raw=True
            )
            result = structured_llm.invoke(messages)
            logger.debug(f"Structured LLM output: {result}")
            logger.info("Structured response parsed successfully.")
            return result

        # No structured response model: fallback to plain content
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
