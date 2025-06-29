from typing import Optional, Type, TypeVar, Union

from PIL import Image as PILImage
from pydantic import BaseModel

from llm_parse.llm.client import call_llm
from llm_parse.models.models import LLMConfig
from llm_parse.utils import get_logger

logger = get_logger(__name__)

ResponseModelType = TypeVar("ResponseModelType", bound=BaseModel)


def dispatch_llm_request(
    config: LLMConfig,
    user_question: Optional[str] = None,
    response_model: Optional[Type[ResponseModelType]] = None,
    image: Optional[PILImage.Image] = None,
) -> Union[str, ResponseModelType]:
    """
    Calls an LLM using the provided configuration and attempts structured parsing if
    requested.

    If structured output fails or is not returned directly, attempts fallback handling.
    This function is useful when supporting providers or modes that may return
    structured output wrapped in dictionaries, or plain text.

    Parameters
    ----------
    config : LLMConfig
        Configuration object for the LLM call.
    user_question : str, optional
        The prompt or question to send to the LLM.
    response_model : Type[BaseModel], optional
        A Pydantic model class used for structured response parsing.
    image : PIL.Image.Image, optional
        Optional image input to pass to the LLM for multimodal support.

    Returns
    -------
    Union[str, BaseModel]
        Structured response if parsed successfully, otherwise a raw string or fallback.

    Raises
    ------
    RuntimeError
        If the LLM call fails or the response is not usable.
    """
    try:
        raw_response = call_llm(
            config=config,
            user_question=user_question,
            response_model=response_model,
            image=image,
        )
    except Exception as e:
        logger.error("Error during LLM invocation", exc_info=True)
        raise RuntimeError(f"LLM invocation failed: {e}") from e

    logger.debug("\n--- Raw LLM Response ---")
    logger.debug(raw_response)

    # Case 1: Structured output successfully parsed
    if isinstance(raw_response, BaseModel):
        logger.info("Structured response returned directly from LLM.")
        return raw_response

    # Case 2: Handle partial or unstructured response
    if isinstance(raw_response, dict) and response_model is not None:
        parsed = raw_response.get("parsed")

        if isinstance(parsed, dict):
            try:
                validated = response_model.model_validate(parsed)
                logger.info(
                    "Successfully validated parsed response using response_model."
                )
                return validated
            except Exception as ve:
                logger.warning(f"Validation failed for parsed response: {ve}")
                raise RuntimeError(f"Validation failed: {ve}") from ve

        elif isinstance(parsed, str):
            logger.warning(
                "Parsed response was string; structured output may have failed."
            )
            return parsed

    logger.warning("Unstructured or unexpected LLM response format.")
    return "⚠️ LLM response could not be parsed or matched expected format."
