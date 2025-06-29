from abc import ABC, abstractmethod
from typing import List

from PIL import Image


class DocumentHandler(ABC):
    """
    Abstract base class for document handlers.
    Each handler is responsible for converting a document into page screenshots.
    """

    @abstractmethod
    def extract_screenshots(self, file_path: str) -> List[Image.Image]:
        """
        Extract page screenshots from a document.

        Parameters:
            file_path (str): Path to the input document.

        Returns:
            List[Image.Image]: A list of page screenshots as PIL Images.
        """
        pass
