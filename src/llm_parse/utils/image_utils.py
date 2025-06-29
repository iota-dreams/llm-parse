from typing import Dict, List

import fitz  # PyMuPDF

from .logger import get_logger

logger = get_logger(__name__)


def extract_image_bboxes_from_page_obj(
    doc: fitz.Document, page_number: int
) -> Dict[str, List[float]]:
    """
    Extracts bounding boxes for all images on a specific page of a loaded PDF document.

    Parameters
    ----------
    doc : fitz.Document
        An already loaded PyMuPDF document object.
    page_number : int
        Zero-based index of the page to extract image bounding boxes from.

    Returns
    -------
    Dict[str, List[float]]
        A dictionary where keys are placeholders (e.g., "image_1", "image_2") and
        values are bounding boxes in the format [x_min, y_min, x_max, y_max].

        If no images are present, returns an empty dictionary.
    """
    try:
        # Our page number for loop starts from 1 to #pages in the document, but fitz
        # counts them 0 to #pages -1. Inorder to correct for this, subtracting -1 from
        # here. We maintain 1 to #pages convention for page numbers
        page_number = page_number - 1
        if not (0 <= page_number < len(doc)):
            raise ValueError(f"Page number {page_number} is out of range.")

        page = doc[page_number]
        image_bboxes: Dict[str, List[float]] = {}

        images = page.get_images(full=True)
        if not images:
            logger.debug(f"No images found on page {page_number}.")
            # Explicit empty result
            return image_bboxes

        for index, img in enumerate(images):
            xref = img[0]
            rect, _ = page.get_image_bbox(xref)

            image_bboxes[f"image_{index + 1}"] = [
                rect.x0,
                rect.y0,
                rect.x1,
                rect.y1,
            ]

        return image_bboxes

    except Exception as e:
        logger.error(
            f"❌ Failed to extract image bounding boxes from page {page_number}: {e}",
            exc_info=True,
        )
        raise RuntimeError(
            f"Image bounding box extraction failed for page {page_number}"
        ) from e
