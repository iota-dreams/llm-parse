import os
from importlib.resources import as_file, files
from pathlib import Path

import yaml

from .logger import get_logger

logger = get_logger(__name__)


class DotDict(dict):
    """
    A dictionary subclass that supports dot notation access for nested dicts.
    """

    def __init__(self, d):
        super().__init__()
        for key, value in d.items():
            self[key] = self._wrap(value)

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(f"'DotDict' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = self._wrap(value)

    def __delattr__(self, key):
        del self[key]

    def _wrap(self, value):
        if isinstance(value, dict):
            return DotDict(value)
        elif isinstance(value, list):
            return [self._wrap(item) for item in value]
        return value


def get_default_config_path(filename: str = "prompts.yaml") -> Path:
    """
    Resolves the default bundled config YAML file by name,
    compatible with both dev and installed environments.

    Parameters:
        filename (str): The name of the config file (e.g. prompts.yaml)

    Returns:
        Path: Resolved path to the bundled config file.
    """
    resource = files("llm_parse.configs").joinpath(filename)
    with as_file(resource) as actual_path:
        return actual_path


def load_config_with_fallback(
    filename: str = "prompts.yaml", dotify: bool = True
) -> DotDict:
    """
    Load config using one of the following strategies:
    1. If CONFIG_ROOT env var is set, try that path.
    2. Try importlib.resources from bundled package.
    3. Fallback to relative path ("./configs/").

    Raises:
        FileNotFoundError: if config file is not found by any strategy.
    """
    log_prefix = "[load_config_with_fallback]"
    # If user sets filename as None
    if not filename:
        filename = "prompts.yaml"
    config_root = os.getenv("CONFIG_ROOT")
    if config_root:
        resolved_path = Path(config_root).expanduser() / filename
        logger.info(f"{log_prefix} 🔍 Trying CONFIG_ROOT: {resolved_path}")
        if resolved_path.exists():
            logger.info(f"{log_prefix} ✅ Found config at CONFIG_ROOT: {resolved_path}")
            return load_config(resolved_path, dotify=dotify)
        else:
            logger.warning(
                f"{log_prefix} ❌ File not found at CONFIG_ROOT: {resolved_path}"
            )

    try:
        resource = files("llm_parse.configs").joinpath(filename)
        logger.info(f"{log_prefix} 📦 Trying importlib.resources: {resource}")
        with as_file(resource) as actual_path:
            logger.info(f"{log_prefix} ✅ Loaded from bundled path: {actual_path}")
            return load_config(actual_path, dotify=dotify)
    except (ModuleNotFoundError, FileNotFoundError) as e:
        logger.warning(f"{log_prefix} ⚠️ importlib.resources failed: {e}")

    fallback_path = Path("configs") / filename
    logger.warning(f"{log_prefix} ⚠️ Final fallback to relative path: {fallback_path}")
    if fallback_path.exists():
        logger.info(f"{log_prefix} ✅ Found at relative path: {fallback_path}")
        return load_config(fallback_path, dotify=dotify)

    error_msg = (
        f"{log_prefix} ❌ Failed to load config from any known location: " f"{filename}"
    )
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)


def load_config(file_path, dotify=True) -> DotDict:
    """
    Loads a YAML file and optionally converts it into a DotDict.

    Parameters:
        file_path (str):
            Path to the YAML file. Can be relative, absolute, or include ~.
        dotify (bool):
            Whether to return a DotDict for dot notation access.

    Returns:
        dict or DotDict: Parsed YAML content.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        yaml.YAMLError: If the YAML is malformed.
    """
    abs_path = Path(file_path).expanduser().resolve(strict=True)
    with open(abs_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return DotDict(data) if dotify else data


def filter_config(config, key_path):
    """
    Traverses a nested dict or DotDict using a list of keys.

    Parameters:
        config (dict or DotDict): The YAML content.
        key_path (list): List of nested keys to traverse.

    Returns:
        Any: Value at the nested path.

    Raises:
        KeyError: If a key in the path does not exist.
        TypeError: If a non-dict is encountered in the path.
    """
    current = config
    for key in key_path:
        if not isinstance(current, dict):
            raise TypeError(
                f"Expected dict at key '{key}', got {type(current).__name__}"
            )
        if key not in current:
            raise KeyError(f"Key '{key}' not found in YAML data.")
        current = current[key]
    return current
