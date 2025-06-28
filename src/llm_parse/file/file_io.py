from io import BytesIO
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

import requests
from PIL import Image as PILImage

from ..utils import get_logger

logger = get_logger(__name__)


def is_url(path: Union[str, Path]) -> bool:
    """Check if a given path is a valid HTTP(S) URL."""
    try:
        result = urlparse(str(path))
        return result.scheme in ("http", "https") and result.netloc != ""
    except Exception:
        return False


def load_image(image_path: Union[str, Path]) -> PILImage.Image:
    """
    Load and process an image from a local file path or an HTTP(S) URL.
    Converts all images to RGB mode.
    """
    if is_url(image_path):
        response = requests.get(str(image_path))
        response.raise_for_status()
        img = PILImage.open(BytesIO(response.content))
    else:
        img = PILImage.open(image_path)

    return img.convert("RGB")
