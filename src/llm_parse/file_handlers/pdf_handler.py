import io
import logging
from pathlib import Path
from typing import Iterator, Optional, Tuple, Union
from urllib.parse import urlparse

import fitz  # PyMuPDF
import requests
from PIL import Image

from llm_parse.file_handlers.base_handler import DocumentHandler
from llm_parse.utils import get_filename

logger = logging.getLogger(__name__)


class PDFHandler(DocumentHandler):
    """
    Handler to process PDF files and extract page screenshots.
    Keeps the PDF document open for efficient multi-page access.
    Supports local file paths, HTTP(S) URLs, and password-protected PDFs.
    """

    def __init__(self, file_path: Union[str, Path], password: str = ""):
        """
        Initializes the PDF handler. Downloads the file if it's a URL.
        Accepts an optional password for encrypted PDFs.

        Parameters:
            file_path (str or Path): Local path or HTTPS URL
            password (str): Password for encrypted PDFs (default: empty string)
        """
        self.file_path = file_path
        self.password = password
        self.file_name = get_filename(file_path)

        try:
            self.document = self._open_document(file_path, password)
            self.total_pages = self.document.page_count

            if self.total_pages == 0:
                logger.warning(f"PDF {file_path} contains no pages.")

        except Exception as e:
            logger.exception("Failed to open PDF document.")
            raise FileNotFoundError(f"Unable to open PDF: {file_path}") from e

    def _open_document(
        self, file_path: Union[str, Path], password: str
    ) -> fitz.Document:
        parsed = urlparse(str(file_path))

        try:
            if parsed.scheme in ("http", "https"):
                logger.info(f"Downloading remote PDF: {file_path}")
                response = requests.get(str(file_path))
                response.raise_for_status()
                doc = fitz.open(stream=response.content, filetype="pdf")
            else:
                doc = fitz.open(str(file_path))

            if doc.is_encrypted:
                if not doc.authenticate(password):
                    raise PermissionError("Incorrect password for encrypted PDF.")

            return doc

        except Exception:
            logger.exception("Error opening or decrypting PDF.")
            raise

    def extract_screenshots(
        self,
        start_page: int = 1,
        end_page: Optional[int] = None,
    ) -> Iterator[Tuple[int, Image.Image, Tuple[float, float]]]:
        """
        Generator that yields screenshots of each page from start_page to end_page
        (inclusive).

        Parameters:
            start_page (int): 1-based index of first page to process.
            end_page (Optional[int]): 1-based index of last page to process (inclusive).

        Yields:
            Tuple[int, Image.Image, Tuple[float, float]]:
                (1-based page number, PIL Image, (width, height) in PDF space)
        """
        if start_page < 1 or start_page > self.total_pages:
            raise ValueError(f"start_page must be between 1 and {self.total_pages}")

        end_page = end_page or self.total_pages
        if end_page < start_page or end_page > self.total_pages:
            raise ValueError(
                f"end_page must be between {start_page} and {self.total_pages}"
            )

        for page_number in range(start_page - 1, end_page):
            try:
                logger.info(f"Rendering page {page_number + 1} of {self.total_pages}")
                page = self.document.load_page(page_number)
                pdf_page_width = page.rect.width
                pdf_page_height = page.rect.height

                pix = page.get_pixmap(dpi=300)  # type: ignore[attr-defined]
                image = Image.open(io.BytesIO(pix.tobytes("png")))

                yield page_number + 1, image, (pdf_page_width, pdf_page_height)

            except Exception as e:
                logger.exception(f"Failed to render page {page_number + 1}")
                raise RuntimeError(
                    f"Rendering failed for page {page_number + 1}"
                ) from e

    def get_screenshot_for_page(self, page_number: int) -> Image.Image:
        """
        Returns a screenshot for a specific 1-based page number.

        Parameters:
            page_number (int): 1-based page index

        Returns:
            PIL.Image.Image: Screenshot of the page

        Raises:
            ValueError: If page number is out of range
            RuntimeError: If rendering fails
        """
        if page_number < 1 or page_number > self.total_pages:
            raise ValueError(
                f"Page {page_number} is out of range (valid: 1 to {self.total_pages})"
            )

        try:
            logger.info(f"Rendering single page {page_number}")
            page = self.document.load_page(page_number - 1)
            pix = page.get_pixmap(dpi=300)  # type: ignore[attr-defined]
            return Image.open(io.BytesIO(pix.tobytes("png")))
        except Exception as e:
            logger.exception(f"Failed to render page {page_number}")
            raise RuntimeError(f"Rendering failed for page {page_number}") from e

    def close(self) -> None:
        """Closes the underlying PDF document."""
        logger.info(f"Closing PDF document: {self.file_path}")
        self.document.close()
