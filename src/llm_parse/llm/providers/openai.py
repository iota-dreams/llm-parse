import getpass
import os

from langchain.chat_models import init_chat_model
from langchain_core.runnables import Runnable

from ...models import LLMConfig
from ...utils import get_logger

logger = get_logger(__name__)

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")


def init_gemini_llm(config: LLMConfig) -> Runnable:
    model = init_chat_model(model=config.model_name, model_provider="openai")
    return model
