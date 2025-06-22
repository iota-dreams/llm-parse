import os
from typing import Optional

from .config_utils import load_config


def supports_multimodal(provider: str, model_name: Optional[str] = None) -> bool:
    """
    Check if the given provider and model support multimodal input,
    based on YAML-defined known capabilities.

    Parameters
    ----------
    provider : str
        LLM provider name (e.g., "openai").
    model_name : str, optional
        The model name to check.

    Returns
    -------
    bool
        True if image input is likely supported; False otherwise.
    """
    provider = provider.lower()
    model_name = (model_name or "").lower()
    multimodal_support = os.path.join(
        os.path.abspath(__file__),
        os.pardir,
        os.pardir,
        os.pardir,
        os.pardir,
        "configs",
        "multimodal_models.yaml",
    )
    MULTIMODAL_MODELS = load_config(file_path=multimodal_support, dotify=True)
    supported_models = MULTIMODAL_MODELS.get(provider, [])
    return any(substr in model_name for substr in supported_models)
