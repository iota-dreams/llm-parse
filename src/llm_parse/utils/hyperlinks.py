from difflib import SequenceMatcher
from typing import List, Tuple

import fitz  # PyMuPDF

from ..models import LLMParse
from .logger import get_logger

logger = get_logger(__name__)


def inject_pdf_hyperlinks(
    llm_parse: LLMParse,
    page_obj: fitz.Page,
    relative_hyperlink_extract: bool = True,
) -> Tuple[LLMParse, List[str]]:
    """
    Injects Markdown-style hyperlinks into llm_parse.text_content
    using URI annotations extracted from the given PyMuPDF page object.

    Supported link types:
    - External: http://, https://
    - Communication: mailto:, tel:
    - (Optional) Internal and relative: /help, #top, #cite.reference

    Parameters
    ----------
    llm_parse : LLMParse
        Parsed page object returned by the LLM, containing parse.text_content.
    page_obj : fitz.Page
        Corresponding page object from PyMuPDF used to extract hyperlink annotations.
    relative_hyperlink_extract : bool, optional
        Whether to include relative and fragment links (e.g., `/section`, `#ref`).
        Defaults to True.

    Returns
    -------
    Tuple[LLMParse, List[str]]
        - Updated llm_parse with Markdown-style hyperlinks injected.
        - List of all valid hyperlinks found on the page (regardless of injection
        success).

    Notes
    -----
    - This function assumes llm_parse.text_content is structurally aligned with the PDF
    layout.
    - Hyperlink anchor text is extracted using spatial clipping from the page (based on
    the hyperlink's bounding box).
    - Multi-line or wrapped hyperlinks are reconstructed from multiple spans and merged
    into a single anchor string.
    - Anchor and URL are treated independently; there's no requirement for the anchor
    to resemble the link.
    - Each URI-anchor pair is injected **once** using either an exact match or a fuzzy
    match (fallback).
    - Repeated anchors (e.g., multiple "Click here" texts) are injected only once for
    the first match found.
    - If the same anchor appears more than once in `text_content`, only the first
    occurrence is replaced.
    - Anchors not found in the content (even after fuzzy matching) are skipped silently.
    - Fuzzy matching (similarity > 0.85) is attempted **only if exact match fails**.
    - Hyperlinks with unsupported or unsafe schemes (e.g., `file://`, `javascript:`)
    are skipped.
    - Hyperlinks without bounding boxes (malformed annotations) are also skipped.
    - If `llm_parse.text_content` is significantly altered or hallucinated by the LLM,
    injection may partially fail.
    """
    # Track (uri, anchor) pairs already injected to avoid duplicates
    injected_once = set()

    # Track all valid URIs found on the page
    all_valid_links = []

    try:
        text_content = llm_parse.text_content or ""
        if not text_content:
            logger.debug(
                "🔍 No text_content found in llm_parse. Skipping hyperlink injection."
            )
            return llm_parse, []

        links = []
        for link in page_obj.get_links():  # type: ignore[attr-defined]
            uri = link.get("uri")
            named_dest = link.get("nameddest")

            resolved_uri = None

            # Case 1: External URI
            if uri:
                uri_lower = uri.lower()
                if uri_lower.startswith(("file://", "data:", "javascript:")):
                    logger.debug(f"⛔ Skipping unsupported scheme: {uri}")
                    continue

                if not relative_hyperlink_extract and not uri_lower.startswith(
                    ("http://", "https://", "mailto:", "tel:")
                ):
                    logger.debug(f"⚠️ Skipping relative URI due to flag: {uri}")
                    continue

                resolved_uri = uri

            # Case 2: Internal target like citation anchor
            elif named_dest and relative_hyperlink_extract:
                resolved_uri = f"#{named_dest.strip()}"

            # Skip if neither valid URI nor internal anchor
            if not resolved_uri:
                continue

            # Bounding box check
            try:
                rect = fitz.Rect(link["from"])
                links.append({"uri": resolved_uri, "rect": rect})
                all_valid_links.append(resolved_uri)
            except Exception:
                logger.warning(
                    f"⚠️ Skipping malformed link with invalid bounding box: {link}"
                )
                continue

        if not links:
            logger.debug("🔍 No valid hyperlinks found with allowed schemes.")
            return llm_parse, []

        logger.debug(f"🔗 Found {len(links)} hyperlink(s) on page.")

        # ----------------------------------------
        # Step 2: Inject each hyperlink into the text content
        # ----------------------------------------
        for link in links:
            uri = link["uri"]
            rect = link["rect"]

            try:
                # Extract spans only within the hyperlink's bounding box
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
                    logger.debug(
                        f"⚠️ No visible text found within hyperlink bbox for URI: {uri}"
                    )
                    continue

                # Merge all span texts to reconstruct full anchor text
                anchor = " ".join(span["text"] for span in spans).strip()
                if not anchor or (uri, anchor) in injected_once:
                    continue

                markdown_link = f"[{anchor}]({uri})"

                # ----------------------------------------
                # Step 2a: Exact match injection
                # ----------------------------------------
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

                # ----------------------------------------
                # Step 2b: Fuzzy match injection (fallback)
                # ----------------------------------------
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
                logger.exception(f"💥 Failed to inject hyperlink for URI: {uri}")
                continue

        # ----------------------------------------
        # Step 3: Update llm_parse with modified content
        # ----------------------------------------
        llm_parse.text_content = text_content

        return llm_parse, all_valid_links

    except Exception:
        logger.exception("💥 Unexpected failure during hyperlink injection.")
        return llm_parse, all_valid_links
