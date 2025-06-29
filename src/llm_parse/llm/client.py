from typing import Optional, Type, Union

from langchain.chat_models import init_chat_model

# LangChain models
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from PIL import Image as PILImage
from pydantic import BaseModel, ValidationError

from ..models import LLMConfig, TableHandler
from ..utils import build_prompt, get_logger

LLMOutput = Union[str, dict, list, BaseModel]
logger = get_logger(__name__)


def call_llm(
    config: LLMConfig,
    response_model: Optional[Type[BaseModel]] = None,
    table_handler: Optional[TableHandler] = TableHandler.html,
    user_question: Optional[str] = None,
    image: Optional[PILImage.Image] = None,
    image_bbox_guide: Optional[dict] = None,
) -> LLMOutput:
    """
    Calls an LLM using the provided config and question, with optional image and
    structured response.

    Parameters
    ----------
    config : LLMConfig
        Configuration containing model, provider, prompt, etc.
        response_model : Type[BaseModel]
        Pydantic model class defining the expected structure of the LLM response.
        The model should match the structure used in parsing logic.
    table_handler : str
        Controls how extracted tables are formatted in the structured output.
        Accepted values are:
            - "html": Tables are returned as HTML strings.
            - "markdown": Tables are returned using Markdown table syntax.
        Defaults to "html".
    user_question : str, optional
        The user's question or prompt.
    image : PIL.Image.Image, optional
        Optional image input. If not provided, falls back to `config.image_path`.
    image_bbox_guide : dict, optional
        A dictionary mapping image placeholders (e.g., "image_1") to bounding box
        coordinates in the format [x_min, y_min, x_max, y_max].
        This can be provided as a guide to help the LLM align visual elements with
        their location on the document page.

        Example:
            {
                "image_1": [72.0, 144.0, 320.5, 288.0],
                "image_2": [100.0, 400.0, 250.0, 500.0]
            }

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

    if image_bbox_guide is None:
        image_bbox_guide = {}

    # Initialize the LLM instance
    llm: BaseChatModel = init_chat_model(
        model=config.model_name,
        model_provider=config.provider,
        temperature=config.temperature or 0.7,
        timeout=getattr(config, "timeout", None),
    )

    # Build prompt with optional image support
    messages = build_prompt(
        config=config,
        table_handler=table_handler,
        user_question=user_question,
        image=image,
        image_bbox_guide=image_bbox_guide,
    )

    logger.info(f"Calling model: {config.model_name}")
    try:
        if response_model:
            # structured_llm = llm.with_structured_output(response_model)
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
