import json
from typing import Any, Optional, Type, TypeVar, Union, cast

from PIL import Image as PILImage
from pydantic import BaseModel

from llm_parse.llm.client import call_llm
from llm_parse.models import LLMConfig
from llm_parse.utils import get_logger

logger = get_logger(__name__)

ResponseModelType = TypeVar("ResponseModelType", bound=BaseModel)


def sanitize_llm_response(data: dict) -> dict:
    """
    Ensures LLM output dicts don't contain nulls where dictionaries are expected.
    """
    for key in ("tables", "image_bbox"):
        val = data.get(key)
        if val in (None, "null", ""):
            data[key] = {}
    return data


def dispatch_llm_request(
    config: LLMConfig,
    response_model: Optional[Type[ResponseModelType]] = None,
    user_question: Optional[str] = None,
    image: Optional[PILImage.Image] = None,
    **prompt_context: Any,
) -> Union[str, ResponseModelType]:
    """
    Calls an LLM using the provided configuration and attempts structured parsing
    if a response model is provided.

    Supports fallback parsing logic in case the model returns a string or fails
    to validate against the schema initially. Accepts arbitrary prompt placeholders.

    Parameters
    ----------
    config : LLMConfig
        Configuration object for the LLM call.
    response_model : Type[BaseModel], optional
        A Pydantic model class used for structured response parsing.
    user_question : str, optional
        The prompt or question to send to the LLM.
    image : PIL.Image.Image, optional
        Optional image input to pass to the LLM for multimodal support.
    **prompt_context : dict
        Arbitrary keyword arguments used as dynamic placeholders in the prompt.
        Example: table_handler, image_bbox_guide, invoice_template, etc.

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
            response_model=response_model,
            user_question=user_question,
            image=image,
            prompt_context=prompt_context,
        )
    except Exception as e:
        logger.error("Error during LLM invocation", exc_info=True)
        raise RuntimeError(f"LLM invocation failed: {e}") from e

    logger.debug("\n--- Raw LLM Response ---")
    logger.debug(raw_response)

    # Case 1: Structured output successfully parsed
    if isinstance(raw_response, BaseModel):
        logger.info("Structured response returned directly from LLM.")
        return cast(ResponseModelType, raw_response)

    # Case 2: Handle partial or unstructured response
    if isinstance(raw_response, dict) and response_model is not None:
        parsed = raw_response.get("parsed")
        raw = raw_response.get("raw")

        # Pydantic validation failed originally, but raw function call exists
        if parsed is None and raw:
            try:
                # Grab the function_call's argument string from raw
                function_call = raw.additional_kwargs.get("function_call", {})
                args_str = function_call.get("arguments", "{}")

                # Convert the argument string to a dictionary
                parsed_dict = json.loads(args_str)

                # Sanitize the dictionary (e.g., handle nulls, fix types, etc.)
                parsed_dict = sanitize_llm_response(parsed_dict)

                # Retry validation using the cleaned-up dictionary
                validated = response_model.model_validate(parsed_dict)

                logger.info("Recovered structured output via post-sanitization.")
                return validated

            except Exception as ve:
                logger.warning(f"Retry after sanitizing parsed LLM output failed: {ve}")
                raise RuntimeError(f"Recovery failed: {ve}") from ve
        #  To handle case when include_raw=True is set to True in
        # llm.with_structured_output function call
        # It returns in this format:
        #     {
        #         "parsed": <parsed_output>,
        #         "raw": <raw_response_from_llm>
        #     }, we check for both `dict` and `BaseModel`
        if isinstance(parsed, (dict, BaseModel)):
            try:
                # If it's already a model, just return it
                if isinstance(parsed, BaseModel):
                    logger.info("Parsed response is already a BaseModel.")
                    return cast(ResponseModelType, parsed)

                # If it's a dict, validate it
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
                f"Parsed response was string; structured output may have failed."
                f"Response: {parsed}"
            )
            return parsed

    logger.warning(
        f"Unstructured or unexpected LLM response format. Response: {raw_response}"
    )
    return (
        "⚠️ LLM response could not be parsed or matched expected format."
        "Response: {raw_response}"
    )
