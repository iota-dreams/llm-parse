from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import Runnable

from ...models import LLMConfig


def init_anthropic_llm(config: LLMConfig) -> Runnable:
    return ChatAnthropic(
        model_name=config.model_name,
        temperature=config.temperature,
        timeout=None,
        stop=None,
    )
