from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from ...models import LLMConfig
from ...utils import get_logger

logger = get_logger(__name__)


def init_gemini_llm(config: LLMConfig) -> Runnable:
    kwargs = {
        "model": config.model_name,
        "temperature": config.temperature,
    }

    if config.safety_settings:
        kwargs["safety_settings"] = [
            {"category": s.category, "threshold": s.threshold}
            for s in config.safety_settings
        ]
        logger.info(f"Applied Gemini safety settings: {kwargs['safety_settings']}")

    return ChatGoogleGenerativeAI(**kwargs)
