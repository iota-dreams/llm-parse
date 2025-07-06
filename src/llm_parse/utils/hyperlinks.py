from difflib import SequenceMatcher
from typing import List, Tuple

import fitz  # PyMuPDF

from ..models import LLMParse
from .logger import get_logger

logger = get_logger(__name__)


def inject_pdf_hyperlinks(
    llm_parse: LLMParse,
    page_obj: fitz.Page,
) -> Tuple[LLMParse, List[str]]:
    """
    Injects Markdown-style hyperlinks into llm_parse.text_content
    using URI annotations extracted from the given PyMuPDF page object.

    Supported links:
    - http:// and https://
    - mailto: and tel:

    All other URI schemes are ignored (e.g., file://, relative paths,
    document fragments).

    Parameters
    ----------
    llm_parse : LLMParse
        Parsed page object returned by the LLM, containing parse.text_content.
    page_obj : fitz.Page
        Corresponding page object from PyMuPDF used to extract hyperlink annotations.

    Returns
    -------
    Tuple[LLMParse, List[str]]
        - Updated llm_parse with Markdown-style hyperlinks injected.
        - List of all valid hyperlinks found on the page (regardless of injection).

    Notes
    -----
    - Injection relies on spatial alignment (IoU overlap) between hyperlink bounding
      boxes and visible text spans on the PDF page.
    - Anchor text and hyperlink URL are treated independently; there is no assumption
      that the anchor resembles the URL.
    - If multiple hyperlinks share the same anchor text (e.g., "Click here"), only
      the **first occurrence** of that anchor in `text_content` will be replaced.
    - Once an anchor is injected, it will not be used again for any subsequent links,
      even if it appears multiple times.
    - Links without matching anchor spans (exact or fuzzy) in `text_content` are
      skipped.
    - This function assumes that `llm_parse.text_content` closely mirrors the layout
      of the original PDF, and may fail to inject links correctly if the structure
      is significantly altered by the LLM.
    """

    injected_once = set()  # Track (uri, anchor) pairs already injected
    all_valid_links = []  # List of all valid URIs found

    try:
        text_content = llm_parse.text_content or ""
        if not text_content:
            logger.debug(
                "No text content available in llm_parse. Skipping hyperlink injection."
            )
            return llm_parse, []

        allowed_schemes = ("http://", "https://", "mailto:", "tel:")

        # Step 1: Collect valid hyperlinks with bounding boxes
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
            logger.debug("No valid hyperlinks found on page.")
            return llm_parse, []

        logger.debug(f"Found {len(links)} hyperlink(s) for injection.")

        # Step 2: For each hyperlink, extract clipped text and inject if anchor found
        for link in links:
            uri = link["uri"]
            rect = link["rect"]

            try:
                # Extract only spans within the hyperlink rectangle
                text_blocks = page_obj.get_text("dict", clip=rect)  # type: ignore[attr-defined]
                spans = []
                for block in text_blocks.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            spans.append(
                                {
                                    "text": span.get("text", "").strip(),
                                    "bbox": fitz.Rect(span["bbox"]),
                                }
                            )

                if not spans:
                    logger.debug(f"No spans found near hyperlink: {uri}")
                    continue

                # Combine all span texts to reconstruct full anchor (handles multi-line)
                anchor = " ".join(span["text"] for span in spans).strip()
                if not anchor or (uri, anchor) in injected_once:
                    continue

                markdown_link = f"[{anchor}]({uri})"

                # Exact match injection
                idx = text_content.find(anchor)
                if idx != -1:
                    text_content = (
                        text_content[:idx]
                        + markdown_link
                        + text_content[idx + len(anchor) :]
                    )
                    injected_once.add((uri, anchor))
                    logger.debug(f"✅ Injected hyperlink: '{anchor}' → {uri}")
                    continue

                # Fallback: fuzzy match
                for word in text_content.split():
                    if (uri, word) in injected_once:
                        continue
                    similarity = SequenceMatcher(None, anchor, word).ratio()
                    if similarity > 0.85:
                        text_content = text_content.replace(word, markdown_link, 1)
                        injected_once.add((uri, anchor))
                        logger.debug(
                            f"🟡 Fuzzy-injected: '{anchor}' ≈ '{word}' → {uri}"
                        )
                        break

            except Exception:
                logger.exception(f"Error while injecting hyperlink: {uri}")
                continue

        # Save updated text back to llm_parse
        llm_parse.text_content = text_content

        return llm_parse, all_valid_links

    except Exception:
        logger.exception("Unexpected failure during hyperlink injection.")
        return llm_parse, all_valid_links
