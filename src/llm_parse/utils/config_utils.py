from pathlib import Path
from typing import Optional

import yaml


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
    Returns the path to the default bundled config file (configs/prompts.yaml).
    """
    # ../../.. from this file → project root
    return Path(__file__).resolve().parents[3] / "configs" / "prompts.yaml"


def load_config_with_fallback(custom_path: Optional[str] = None, dotify: bool = True):
    """
    Loads user-provided config if given, otherwise loads the default prompts.yaml.

    Parameters:
        custom_path (str, optional): User-supplied config path.
        dotify (bool): Whether to return a DotDict.

    Returns:
        DotDict or dict
    """
    path = Path(custom_path).expanduser() if custom_path else get_default_config_path()
    return load_config(path, dotify=dotify)


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
