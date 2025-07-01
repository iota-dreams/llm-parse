import json
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

from pydantic import BaseModel

from .logger import get_logger

logger = get_logger(__name__)


def ensure_output_dir(output_dir: Union[str, Path, None]) -> Union[Path, None]:
    """
    Ensures the output directory exists if provided.

    Returns:
        Path: The Path object or None if not set.
    """
    if not output_dir:
        return None

    if not isinstance(output_dir, (str, Path)):
        raise TypeError(f"output_dir must be str, Path or None, got {type(output_dir)}")

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured output directory exists: {path}")
    return path


def save_model(
    model: Union[BaseModel, str],
    output_path: Union[str, Path],
    indent: int = 2,
    encoding: str = "utf-8",
    mode: str = "json",
):
    """
    Save a Pydantic model or raw string to a file.

    Parameters:
        model (BaseModel | str): The object to save.
        output_path (str | Path): Destination path.
        indent (int): Indentation for JSON (ignored for str).
        encoding (str): File encoding.
        mode (str): 'json' for structured output, 'text' for plain text.
    """
    output_path = Path(output_path)

    if isinstance(model, BaseModel):
        if mode == "json":
            content = model.model_dump(mode="json")
            with output_path.open("w", encoding=encoding) as f:
                json.dump(content, f, indent=indent, ensure_ascii=False)
        elif mode == "text":
            with output_path.open("w", encoding=encoding) as f:
                f.write(str(model))
        else:
            raise ValueError(f"Unsupported mode '{mode}'. Use 'json' or 'text'.")

    elif isinstance(model, str):
        with output_path.open("w", encoding=encoding) as f:
            f.write(model)

    else:
        raise TypeError(f"Expected BaseModel or str, got {type(model)}")


def load_model(model_class: type[BaseModel], path: Union[str, Path]) -> BaseModel:
    """
    Load any Pydantic model from a JSON file.

    Parameters:
        model_class (type[BaseModel]): The model class (e.g., LLMParseResult)
        path (str | Path): Path to load from.

    Returns:
        BaseModel: An instance of the model.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return model_class.model_validate(data)


def get_filename(path: Union[str, Path]) -> str:
    """
    Extracts the filename (with extension) from a local path or cloud URL.

    Parameters:
        path (Union[str, Path]): File path or cloud URL.

    Returns:
        str: Filename including extension.

    Raises:
        ValueError: If the filename cannot be determined.
    """
    try:
        path_str = str(path)
        parsed = urlparse(path_str)

        # For URLs or cloud paths like s3://, gs://, etc.
        if parsed.scheme and parsed.path:
            filename = Path(parsed.path).name
        else:
            filename = Path(path_str).name

        if not filename:
            raise ValueError(f"No filename found in path: {path_str}")

        return filename

    except Exception as e:
        logger.error(f"Failed to extract filename from '{path}': {e}")
        raise


def get_filename_without_extension(path: Union[str, Path]) -> str:
    """
    Extracts the filename (without extension) from a local path or cloud URL.

    Parameters:
        path (Union[str, Path]): File path or cloud URL.

    Returns:
        str: Filename without extension.

    Raises:
        ValueError: If the filename cannot be determined.
    """
    try:
        filename = get_filename(path)
        return Path(filename).stem
    except Exception as e:
        logger.error(f"Failed to extract filename stem from '{path}': {e}")
        raise
