import argparse


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments to override default values.
    """
    parser = argparse.ArgumentParser(description="Parse PDF using LLM-based pipeline.")
    parser.add_argument("--file", type=str, help="Path to input PDF file")
    parser.add_argument("--start-page", type=int, help="Start page number (1-based)")
    parser.add_argument("--end-page", type=int, help="End page number (inclusive)")
    parser.add_argument(
        "--enable-image-description",
        action="store_true",
        help="Enable image captioning",
    )
    parser.add_argument(
        "--write-to-disk", action="store_true", help="Write outputs to disk"
    )
    parser.add_argument(
        "--return-images",
        choices=["path", "base64", "none"],
        help="Return image format",
    )
    parser.add_argument("--output-dir", type=str, help="Directory to save output files")
    parser.add_argument(
        "--denormalize-images",
        action="store_true",
        help="Apply denormalization to images",
    )
    parser.add_argument(
        "--question", type=str, help="User question for LLM to answer per page"
    )
    parser.add_argument("--password", type=str, help="Password for encrypted PDFs")
    parser.add_argument(
        "--postprocess",
        action="store_true",
        help="Enable document-level post-processing",
    )
    return parser.parse_args()
