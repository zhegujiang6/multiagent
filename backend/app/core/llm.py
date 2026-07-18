"""OpenAI-compatible client factory for LLM interactions.

Supports any OpenAI-compatible API (Anthropic via proxy, Alibaba MaaS, etc.)
"""

from openai import AsyncOpenAI
from app.core.config import settings

_async_client: AsyncOpenAI | None = None


def get_async_llm_client() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base or None,
            timeout=30.0,
            max_retries=1,
        )
    return _async_client


DEFAULT_MODEL = settings.llm_model
FAST_MODEL = settings.llm_fast_model
