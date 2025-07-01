from __future__ import annotations

from typing import Dict, List, Optional

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

from .logger import get_logger

logger = get_logger(__name__)


def normalize_bbox(
    bbox: List[float], page_width: float, page_height: float
) -> List[float]:
    """
    Normalize a bounding box to the [0.0, 1.0] range.

    Parameters
    ----------
    bbox : list of float
        Bounding box as [x_min, y_min, x_max, y_max] in page units.
    page_width : float
        Width of the page.
    page_height : float
        Height of the page.

    Returns
    -------
    list of float
        Normalized bounding box in the same format.
    """
    x_min, y_min, x_max, y_max = bbox
    return [
        x_min / page_width,
        y_min / page_height,
        x_max / page_width,
        y_max / page_height,
    ]


def extract_image_bboxes_from_page_obj(
    doc: fitz.Document,
    page_number: int,
    normalize: bool = True,
    hide_invisible: bool = True,
) -> Dict[str, List[float]]:
    """
    Extracts bounding boxes for images on a specific page of a loaded PDF document.

    Parameters
    ----------
    doc : fitz.Document
        An already loaded PyMuPDF document object.
    page_number : int
        One-based index of the page to extract image bounding boxes from.
    normalize : bool, optional
        If True, normalize bounding boxes to [0.0, 1.0] based on page size.
    hide_invisible : bool, optional
        If True, skips images with empty or tiny bounding boxes
        (i.e., invisible images).

    Returns
    -------
    Dict[str, List[float]]
        A dictionary where keys are placeholders (e.g., "image_1", "image_2") and
        values are bounding boxes in the format [x_min, y_min, x_max, y_max].

        If no qualifying images are present, returns an empty dictionary.
    """
    try:
        page_number -= 1
        if not (0 <= page_number < len(doc)):
            raise ValueError(f"Page number {page_number + 1} is out of range.")

        page = doc[page_number]
        image_bbox_guide: Dict[str, List[float]] = {}

        images = page.get_images(full=True)
        if not images:
            logger.debug(f"No images found on page {page_number + 1}.")
            return image_bbox_guide

        page_width = page.rect.width
        page_height = page.rect.height

        for index, img in enumerate(images):
            rect_tuple = page.get_image_bbox(img)
            rect = rect_tuple[0] if isinstance(rect_tuple, tuple) else rect_tuple

            # Skip small and invisible/tiny images
            if hide_invisible and (rect.is_empty or (rect.width * rect.height) < 1.0):
                logger.debug(f"Skipping invisible/tiny image at index {index + 1}")
                continue

            bbox = [rect.x0, rect.y0, rect.x1, rect.y1]

            if normalize:
                bbox = normalize_bbox(bbox, page_width, page_height)

            image_bbox_guide[f"image_{index + 1}"] = bbox

        return image_bbox_guide

    except Exception as e:
        logger.error(
            f"❌ Failed to extract image bounding boxes from page {page_number + 1}:"
            "{e}",
            exc_info=True,
        )
        raise RuntimeError(
            f"Image bounding box extraction failed for page {page_number + 1}"
        ) from e


def denormalize_all_bboxes(
    bbox_dict: Dict[str, List[float]],
    page_width: float,
    page_height: float,
) -> Dict[str, List[float]]:
    """
    Denormalize bounding boxes from normalized [0.0-1.0] format to absolute page
    coordinates.

    Parameters
    ----------
    bbox_dict : Dict[str, List[float]]
        Dictionary of normalized bounding boxes with keys like "image_1" and values
        as [x_min, y_min, x_max, y_max] where all values are between 0.0 and 1.0.
    page_width : float
        Width of the PDF page or image in points.
    page_height : float
        Height of the PDF page or image in points.

    Returns
    -------
    Dict[str, List[float]]
        Dictionary with the same keys as `bbox_dict` but with absolute coordinate
        values.

    Notes
    -----
    - If `bbox_dict` is empty, an empty dictionary is returned.
    - Invalid entries (non-list or not length 4) are skipped with a warning.
    """
    # Early exit if the dictionary is empty
    if not bbox_dict:
        logger.debug("Received empty bbox_dict; returning empty result.")
        return {}

    denormalized = {}

    for key, bbox in bbox_dict.items():
        # Validate that each value is a list of exactly four float-like numbers
        if not isinstance(bbox, list) or len(bbox) != 4:
            logger.warning(f"Skipping invalid bbox for key '{key}': {bbox}")
            continue

        try:
            x_min, y_min, x_max, y_max = bbox

            # Denormalize coordinates using page dimensions
            denormalized[key] = [
                x_min * page_width,
                y_min * page_height,
                x_max * page_width,
                y_max * page_height,
            ]

        except Exception as e:
            logger.error(
                f"Failed to denormalize bbox for key '{key}': {bbox}. Error: {e}",
                exc_info=True,
            )
            continue

    if not denormalized:
        logger.debug("No valid bboxes found to denormalize.")

    return denormalized


def crop_images_from_bbox(
    image: Image.Image,
    image_bbox: Dict[str, List[float]],
    *,
    scale_factor: float = 1.0,
    normalized: bool = False,
) -> Dict[str, Image.Image]:
    """
    Extract cropped regions from an image using bounding box coordinates.

    Parameters
    ----------
    image : PIL.Image.Image
        The source image (e.g., a full-page screenshot or scan).
    image_bbox : dict[str, list[float]]
        Dictionary mapping placeholder keys (e.g., "image_1") to bounding boxes:
        [x_min, y_min, x_max, y_max].
    scale_factor : float, default 1.0
        Applied to the bbox coordinates to scale them to the image space.
        Use this when bbox is in a different unit (e.g., PDF points).
    normalized : bool, default False
        Whether the bounding box coordinates are in normalized form (i.e., between 0.0
        and 1.0).

    Returns
    -------
    dict[str, PIL.Image.Image]
        Dictionary mapping the original keys (e.g., "image_1") to cropped PIL image
        objects.
    """
    cropped_images: Dict[str, Image.Image] = {}

    width, height = image.size

    for key, box in image_bbox.items():
        if not isinstance(box, list) or len(box) != 4:
            logger.warning(f"Skipping invalid bbox for key: {key}")
            continue

        x_min, y_min, x_max, y_max = box

        if normalized:
            x_min *= width
            x_max *= width
            y_min *= height
            y_max *= height

        x_min, y_min, x_max, y_max = [
            int(coord * scale_factor) for coord in (x_min, y_min, x_max, y_max)
        ]

        x_min = max(0, min(x_min, width))
        x_max = max(0, min(x_max, width))
        y_min = max(0, min(y_min, height))
        y_max = max(0, min(y_max, height))

        if x_max <= x_min or y_max <= y_min:
            logger.warning(f"Invalid crop region for key {key}: zero or negative size.")
            continue

        try:
            cropped = image.crop((x_min, y_min, x_max, y_max))
            cropped_images[key] = cropped
            logger.debug(
                f"Cropped image '{key}' at [{x_min}, {y_min}, {x_max}, {y_max}]"
            )
        except Exception as e:
            logger.exception(f"Failed to crop image for key '{key}': {e}")

    return cropped_images


def annotate_image_with_bbox(
    image: Image.Image,
    image_bbox: Dict[str, List[float]],
    *,
    scale_factor: float = 1.0,
    normalized: bool = False,
    font_size: int = 14,
    color_map: Optional[Dict[str, str]] = None,
) -> Image.Image:
    """
    Draw bounding boxes and key labels (e.g. ``image_1``) on a copy of *image*.

    Parameters
    ----------
    image : PIL.Image.Image
        The source image to annotate.
    image_bbox : dict[str, list[float]]
        Mapping from placeholder keys (``"image_1"``, ``"table_3"`` …)
        to bounding-box coordinates ``[x_min, y_min, x_max, y_max]``.
    scale_factor : float, default 1.0
        Multiplier applied to bbox coordinates after any normalisation.
    normalized : bool, default False
        Set ``True`` when bbox coordinates are relative numbers in ``[0, 1]``.
    font_size : int, default 14
        Size of the text labels in points.
    color_map : dict[str, str], optional
        Optional custom color map for prefixes like "image", "table", etc.

    Returns
    -------
    PIL.Image.Image
        A copy of the image with boxes and labels drawn.
    """
    default_map = {
        "image": "#FF0000",
        "table": "#00FF00",
        "figure": "#FFA500",
        "link": "#0000FF",
        "hyperlink": "#0000FF",
    }

    effective_map = {**default_map, **(color_map or {})}
    effective_map["link"] = effective_map["hyperlink"] = "#0000FF"

    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    width, height = image.size

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
        logger.warning("Falling back to default font for annotation labels.")

    for key, box in image_bbox.items():
        if not isinstance(box, list) or len(box) != 4:
            logger.warning(f"Skipping invalid bbox entry for key: {key}")
            continue

        x_min, y_min, x_max, y_max = box

        if normalized:
            x_min *= width
            x_max *= width
            y_min *= height
            y_max *= height

        x_min, y_min, x_max, y_max = [
            int(coord * scale_factor) for coord in (x_min, y_min, x_max, y_max)
        ]

        x_min = max(0, min(x_min, width))
        x_max = max(0, min(x_max, width))
        y_min = max(0, min(y_min, height))
        y_max = max(0, min(y_max, height))

        prefix = key.split("_", 1)[0]
        box_colour = effective_map.get(prefix, "#FF00FF")

        draw.rectangle([x_min, y_min, x_max, y_max], outline=box_colour, width=2)

        label = key
        text_w = font.getlength(label)
        text_h = font_size

        label_x = x_min + 2
        label_y = y_min + 2

        draw.rectangle(
            [label_x, label_y, label_x + text_w + 4, label_y + text_h + 4],
            fill=box_colour,
        )
        draw.text((label_x + 2, label_y + 2), label, fill="white", font=font)

        logger.debug(f"Annotated bbox '{key}' at [{x_min}, {y_min}, {x_max}, {y_max}]")

    return annotated
