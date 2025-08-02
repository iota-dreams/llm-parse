import os
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


def get_default_config_path() -> Path:
    """
    Resolves the default bundled prompts.yaml file.
    Works both in development and after pip install.
    """
    # First: try relative to the installed package (e.g., site-packages)
    installed_path = Path(__file__).resolve().parents[2] / "configs" / "prompts.yaml"
    if installed_path.exists():
        return installed_path

    # Fallback: try project root (during development)
    dev_path = Path(__file__).resolve().parents[3] / "configs" / "prompts.yaml"
    if dev_path.exists():
        return dev_path

    raise FileNotFoundError(
        "Could not find bundled prompts.yaml in expected locations."
    )


def load_config_with_fallback(
    custom_path: Optional[Union[str, Path]] = None, dotify: bool = True
) -> DotDict:
    """
    Load configuration from YAML file using the following fallback order:
    1. `custom_path` argument (explicit override)
    2. `PROMPT_CONFIG_PATH` environment variable
    3. `CONFIG_ROOT` environment variable + 'prompts.yaml'
    4. Bundled fallback config in `configs/prompts.yaml`

    Args:
        custom_path (Optional[Union[str, Path]]):
            Direct override for config file location.
        dotify (bool):
            Whether to return result as a DotDict for attribute-style access.

    Returns:
        DotDict or dict: Parsed configuration content.

    Raises:
        FileNotFoundError: If the resolved config file path doesn't exist.
        yaml.YAMLError: If the YAML content is malformed.
    """
    if custom_path is not None:
        resolved_path = Path(custom_path).expanduser()
        source = "custom_path"

    else:
        env_prompt_path = os.getenv("PROMPT_CONFIG_PATH")
        if env_prompt_path is not None:
            resolved_path = Path(env_prompt_path).expanduser()
            source = "PROMPT_CONFIG_PATH"
        else:
            config_root = os.getenv("CONFIG_ROOT")
            if config_root is not None:
                resolved_path = Path(config_root).expanduser() / "prompts.yaml"
                source = "CONFIG_ROOT"
            else:
                resolved_path = get_default_config_path()
                source = "default bundled config"

    logger.info(f"🔧 Loading prompt config from ({source}): {resolved_path}")
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
