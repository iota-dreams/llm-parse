from difflib import SequenceMatcher
from typing import Tuple

import fitz  # PyMuPDF

from ..models import LLMParseResult
from .logger import get_logger

logger = get_logger(__name__)


def inject_pdf_hyperlinks(
    parsed_page: LLMParseResult,
    page_obj: fitz.Page,
) -> Tuple[LLMParseResult, list[str]]:
    """
    Injects Markdown-style hyperlinks into parsed_page.parse.text_content
    using URI annotations extracted from the given PyMuPDF page object.

    Supported links:
    - http:// and https://
    - mailto: and tel:

    All other URI schemes are ignored (e.g., file://, relative paths,
    document fragments).

    Parameters:
        parsed_page: LLMParseResult
            Parsed page object returned by the LLM, containing parse.text_content.
        page_obj: fitz.Page
            Corresponding page object from PyMuPDF used to extract hyperlink
            annotations.

    Returns:
        Tuple[LLMParseResult, List[str]]:
            - Updated parsed_page with Markdown-style hyperlinks injected.
            - List of all valid hyperlinks found on the page (regardless of injection).
    """
    # Track unique anchor texts that have already been replaced
    injected_once = set()

    # Store all valid hyperlinks (used or unused)
    all_valid_links = []

    try:
        # Extract the existing text content from the parsed page
        text_content = parsed_page.parse.text_content or ""
        if not text_content:
            logger.debug(
                "No text content in parsed_page. Skipping hyperlink injection."
            )
            return parsed_page, []

        # Acceptable schemes for link injection
        allowed_schemes = ("http://", "https://", "mailto:", "tel:")

        # Extract all hyperlinks from the PDF page that match allowed schemes
        links = []
        for link in page_obj.get_links():  # type: ignore[attr-defined]
            uri = link.get("uri")
            if uri and any(
                uri.lower().startswith(scheme) for scheme in allowed_schemes
            ):
                try:
                    rect = fitz.Rect(link["from"])
                    links.append({"uri": uri, "rect": rect})
                    all_valid_links.append(uri)
                except Exception:
                    logger.warning(f"Skipping malformed link with invalid bbox: {link}")
                    continue

        if not links:
            logger.debug("No hyperlinks with supported schemes found.")
            return parsed_page, []

        logger.debug(f"Found {len(links)} valid hyperlink(s) on page.")

        # Collect visible text spans and their bounding boxes from the page
        spans = []
        try:
            for block in page_obj.get_text("dict")["blocks"]:  # type: ignore[attr-defined]
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        spans.append(
                            {
                                "text": span.get("text", ""),
                                "bbox": fitz.Rect(span["bbox"]),
                            }
                        )
        except Exception:
            logger.exception("Failed to extract text spans from PDF page.")
            return parsed_page, all_valid_links

        logger.debug(f"Collected {len(spans)} text spans for anchor detection.")

        # Attempt to match each link to a visible anchor span
        for link in links:
            uri = link["uri"]
            rect = link["rect"]

            for span in spans:
                anchor = span["text"]
                if not anchor or anchor in injected_once:
                    continue

                # Check for visual overlap using Intersection over Union (IoU)
                intersection = rect & span["bbox"]
                if intersection.is_empty:
                    continue

                iou = intersection.get_area() / rect.get_area()
                if iou < 0.1:
                    continue  # Not enough overlap to consider match

                # Construct Markdown-style hyperlink
                markdown_link = f"[{anchor}]({uri})"

                # Attempt exact match and replacement in text_content
                idx = text_content.find(anchor)
                if idx != -1:
                    text_content = (
                        text_content[:idx]
                        + markdown_link
                        + text_content[idx + len(anchor) :]
                    )
                    injected_once.add(anchor)
                    logger.debug(f"✅ Injected hyperlink: '{anchor}' → {uri}")
                    break  # Proceed to next link

                # Fallback: use fuzzy match if exact not found
                for word in text_content.split():
                    if word in injected_once:
                        continue
                    similarity = SequenceMatcher(None, anchor, word).ratio()
                    if similarity > 0.85:
                        text_content = text_content.replace(word, markdown_link, 1)
                        injected_once.add(anchor)
                        logger.debug(
                            f"🟡 Fuzzy-injected: '{anchor}' ≈ '{word}' → {uri}"
                        )
                        break

                # Whether injected or not, go to next link
                break

        # Save updated content back to the model
        parsed_page.parse.text_content = text_content

        return parsed_page, all_valid_links

    except Exception:
        logger.exception("Failed to inject hyperlinks into parsed page content.")
        return parsed_page, all_valid_links
