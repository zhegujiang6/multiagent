"""BaseAgent — abstract base class for all agents in the system."""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from typing import Any

from openai import AsyncOpenAI

from app.schemas.agent import AgentState

logger = logging.getLogger("customer_service.agents")


def message_text(message: Any) -> str:
    """Return only the human-readable body from dict or LangChain messages."""
    if message is None:
        return ""
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        content = message.get("content", "")
    else:
        content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return "\n".join(parts)
    return str(content) if content is not None else ""


def _extract_response_content(resp: Any) -> str | None:
    """Extract text content from an LLM response, handling non-standard formats.

    OpenAI standard: resp.choices[0].message.content
    Alibaba MaaS compatible-mode: resp.text (choices is None)
    """
    # Standard ChatCompletion format
    if resp.choices and len(resp.choices) > 0:
        choice = resp.choices[0]
        if choice.message and choice.message.content:
            return choice.message.content

    # Alibaba MaaS compatible-mode fallback
    if hasattr(resp, "text") and resp.text is not None:
        return resp.text

    # Last resort — try to get anything
    if hasattr(resp, "choices") and resp.choices:
        try:
            return str(resp.choices[0])
        except Exception:
            pass

    return None


class BaseAgent(ABC):
    """Abstract base for all agents.

    Each agent has:
    - A name (for logging/routing)
    - A system prompt (YAML template or string)
    - An execute method that takes AgentState and returns partial state updates
    """

    def __init__(self, name: str, llm_client: AsyncOpenAI):
        self.name = name
        self.llm = llm_client

    @abstractmethod
    async def execute(self, state: AgentState) -> dict[str, Any]:
        """Execute this agent and return partial state updates.

        Args:
            state: Current AgentState from the LangGraph

        Returns:
            Dict of fields to merge into the AgentState
        """
        ...

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
        max_tokens: int = 1024,
        timeout: float = 15.0,
    ) -> str:
        """Convenience method for calling the LLM (OpenAI-compatible).

        Handles both standard ChatCompletion (choices[0].message.content)
        and Alibaba MaaS compatible-mode (resp.text) response formats.

        Args:
            timeout: Max seconds to wait for the API response (default 15s).
        """
        start = time.monotonic()
        try:
            resp = await asyncio.wait_for(
                self.llm.chat.completions.create(
                    model=model or "qwen-max",
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                ),
                timeout=timeout,
            )
            elapsed = int((time.monotonic() - start) * 1000)

            # Handle both standard and Alibaba MaaS response formats
            content = _extract_response_content(resp)

            logger.info(
                f"[{self.name}] LLM call: {elapsed}ms, "
                f"content_len={len(content) if content else 0}"
            )
            return content or ""
        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error(f"[{self.name}] LLM call timed out after {elapsed}ms")
            raise
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error(f"[{self.name}] LLM call failed after {elapsed}ms: {e}")
            raise
