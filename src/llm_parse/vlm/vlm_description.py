from typing import Dict

from PIL import Image as PILImage

from ..llm.dispatcher import dispatch_llm_request
from ..models import ImageDescription, LLMConfig
from ..utils import get_logger

logger = get_logger(__name__)


def vlm_description(
    images: Dict[str, PILImage.Image],
    config: LLMConfig,
    prompt: str,
) -> Dict[str, ImageDescription]:
    """
    Describes each image using an LLM and returns a mapping from placeholder keys to
    structured descriptions.

    Parameters
    ----------
    images : Dict[str, PIL.Image.Image]
        Dictionary of cropped images keyed by placeholders like "image_1".

    config : LLMConfig
        LLM configuration for generating vision-language responses.

    prompt : str, optional
        Prompt to use for describing each image.

    Returns
    -------
    Dict[str, ImageDescription]
        A dictionary mapping image keys like "image_1" to ImageDescription models.
    """
    logger.info(f"Generating image descriptions for {len(images)} image(s)...")

    descriptions: Dict[str, ImageDescription] = {}

    for key, img in images.items():
        logger.debug(f"Describing image: {key}")

        try:
            # Send LLM request for this image
            response = dispatch_llm_request(
                config=config,
                response_model=ImageDescription,
                user_question=prompt,
                image=img,
            )

            if isinstance(response, ImageDescription):
                logger.info(f"🖼️ Successfully described {key}")
                descriptions[key] = response
            else:
                logger.warning(
                    f"Unexpected response type for {key}: {type(response)}. "
                    "Falling back to string description."
                )
                descriptions[key] = ImageDescription(
                    description=str(response), vlm_confidence=None
                )

        except Exception as e:
            logger.exception(f"Failed to describe image '{key}': {e}")
            descriptions[key] = ImageDescription(
                description="⚠️ Failed to generate description.",
                vlm_confidence=None,
            )

    logger.info("Image description generation complete.")
    return descriptions
