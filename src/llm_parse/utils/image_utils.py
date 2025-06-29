from typing import Dict, List

import fitz  # PyMuPDF

from .logger import get_logger

logger = get_logger(__name__)


def extract_image_bboxes_from_page(
    pdf_path: str, page_number: int
) -> Dict[str, List[float]]:
    """
    Extracts bounding boxes for all images on a specific page of a PDF document.

    Parameters:
        pdf_path (str): The path to the input PDF file.
        page_number (int): The zero-based index of the page to analyze.

    Returns:
        Dict[str, List[float]]: A dictionary where each key is a placeholder string
        (e.g., "image_1", "image_2") and each value is a bounding box in the format:
        [x_min, y_min, x_max, y_max].

    Raises:
        ValueError: If the provided page number is out of range.
        RuntimeError: If any internal error occurs during image extraction.
    """
    try:
        # Open the PDF document
        doc = fitz.open(pdf_path)

        # Validate that the page number is within bounds
        if not (0 <= page_number < len(doc)):
            raise ValueError(f"Page number {page_number} is out of range for this PDF")

        # Load the specified page
        page = doc[page_number]
        image_bboxes = {}

        # Iterate over all images on the page
        for index, img in enumerate(page.get_images(full=True)):
            xref = img[0]  # Image reference ID

            # Unpack the bounding box and transformation matrix
            rect, _ = page.get_image_bbox(xref)

            # Store the bounding box as a list of coordinates
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
