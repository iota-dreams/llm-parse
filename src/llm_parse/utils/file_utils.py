import json
from pathlib import Path
from typing import List, Union
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


def to_serializable(obj):
    """Recursively convert Pydantic models and nested structures into JSON-serializable
    dicts."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    elif isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_serializable(item) for item in obj]
    else:
        return obj


def save_model(
    model: Union[BaseModel, List[BaseModel], dict, str],
    output_path: Union[str, Path],
    indent: int = 2,
    encoding: str = "utf-8",
    mode: str = "json",
):
    """
    Save a Pydantic model, list of models, raw string, or dict to a file.

    Parameters
    ----------
    model : BaseModel | List[BaseModel] | dict | str
        The object to save.

    output_path : str | Path
        Destination path for saving.

    indent : int, optional
        Indentation for JSON output (ignored for plain text).

    encoding : str, optional
        File encoding to use. Default is 'utf-8'.

    mode : str, optional
        - 'json' for structured output (default)
        - 'text' for plain string output
    """
    output_path = Path(output_path)

    if mode == "json":
        if isinstance(model, BaseModel):
            content = model.model_dump(mode="json")
        elif isinstance(model, list) and all(isinstance(m, BaseModel) for m in model):
            content = [m.model_dump(mode="json") for m in model]
        elif isinstance(model, dict):
            content = to_serializable(model)
        else:
            raise TypeError(
                f"Expected BaseModel, list of BaseModel, or dict in JSON mode, got "
                f"{type(model)}"
            )

        with output_path.open("w", encoding=encoding) as f:
            json.dump(content, f, indent=indent, ensure_ascii=False)

    elif mode == "text":
        if isinstance(model, str):
            with output_path.open("w", encoding=encoding) as f:
                f.write(model)
        else:
            with output_path.open("w", encoding=encoding) as f:
                f.write(str(model))

    else:
        raise ValueError(f"Unsupported mode '{mode}'. Use 'json' or 'text'.")


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
