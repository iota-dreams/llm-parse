import os
from importlib.resources import as_file, files
from pathlib import Path
from typing import Optional, Union

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
    custom_path: Optional[Union[str, Path]] = None,
    *,
    dotify: bool = True,
    filename: str = "prompts.yaml",
) -> DotDict:
    """
    Load a configuration YAML file using a prioritized fallback strategy.

    The resolution order is:
    1. `custom_path` argument (explicit override)
    2. `PROMPT_CONFIG_PATH` environment variable
    3. `CONFIG_ROOT` environment variable + `filename`
    4. Bundled fallback config in `llm_parse/configs/{filename}`

    Parameters
    ----------
    custom_path : str or Path, optional
        Direct override path for the config file.
    dotify : bool, default=True
        Whether to return the result as a DotDict for attribute-style access.
    filename : str, default="prompts.yaml"
        Name of the config file to load.

    Returns
    -------
    DotDict or dict
        Parsed configuration content from the resolved YAML file.

    Raises
    ------
    FileNotFoundError
        If the resolved config file path doesn't exist.
    yaml.YAMLError
        If the YAML file is malformed.
    ValueError
        If required environment variables are set but empty.
    """
    if custom_path is not None:
        resolved_path = Path(custom_path).expanduser()
        source = "custom_path"

    elif os.getenv("PROMPT_CONFIG_PATH"):
        prompt_config_path = os.getenv("PROMPT_CONFIG_PATH")
        if not prompt_config_path:
            raise ValueError("PROMPT_CONFIG_PATH environment variable is not set.")
        resolved_path = Path(prompt_config_path).expanduser()
        source = "PROMPT_CONFIG_PATH"

    elif os.getenv("CONFIG_ROOT"):
        config_root = os.getenv("CONFIG_ROOT")
        if not config_root:
            raise ValueError("CONFIG_ROOT environment variable is not set.")
        resolved_path = Path(config_root).expanduser() / filename
        source = "CONFIG_ROOT"

    else:
        # Use importlib.resources for bundled config
        resource = files("llm_parse.configs").joinpath(filename)
        source = "default bundled config"
        logger.info(f"🔧 Loading config '{filename}' from ({source})")
        with as_file(resource) as actual_path:
            logger.info(f"Loading config from {actual_path}")
            return load_config(actual_path, dotify=dotify)

    logger.info(f"🔧 Loading config '{filename}' from ({source}): {resolved_path}")
    return load_config(resolved_path, dotify=dotify)


def load_config(file_path, dotify=True):
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
