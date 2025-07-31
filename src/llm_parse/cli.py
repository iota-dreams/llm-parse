import argparse


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments to override default values.
    """
    parser = argparse.ArgumentParser(description="Parse PDF using LLM-based pipeline.")
    parser.add_argument("-f", "--file", type=str, help="Path to input PDF file")
    parser.add_argument(
        "--config-path",
        type=str,
        default=None,
        help="Path to YAML config file (defaults to built-in config if not provided)",
    )
    parser.add_argument(
        "-s", "--start-page", type=int, help="Start page number (1-based)"
    )
    parser.add_argument(
        "-e", "--end-page", type=int, help="End page number (inclusive)"
    )
    parser.add_argument(
        "-i",
        "--enable-image-description",
        action="store_true",
        help="Enable image captioning",
    )
    parser.add_argument(
        "-w",
        "--write-to-disk",
        action="store_true",
        help="Write outputs to disk",
    )
    parser.add_argument(
        "-r",
        "--return-images",
        choices=["path", "base64", "none"],
        help="Return image format",
    )
    parser.add_argument(
        "-o", "--output-dir", type=str, help="Directory to save output files"
    )
    parser.add_argument(
        "-d",
        "--denormalize-images",
        action="store_true",
        help="Apply denormalization to images",
    )
    parser.add_argument(
        "-q",
        "--question",
        type=str,
        help="User question for LLM to answer per page",
    )
    parser.add_argument(
        "-p", "--password", type=str, help="Password for encrypted PDFs"
    )
    parser.add_argument(
        "--postprocess",
        action="store_true",
        help="Enable document-level post-processing",
    )
    return parser.parse_args()
