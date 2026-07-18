"""Sentiment Analyzer Agent — real-time emotion detection and trend tracking."""

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent, message_text
from app.schemas.agent import AgentState
from app.core.llm import FAST_MODEL

logger = logging.getLogger("customer_service.agents.sentiment")

SYSTEM_PROMPT = """你是一个专业的客服情绪分析器。分析用户消息中的情绪状态。

## 情绪标签（5类）：
1. satisfied - 满意/开心/感谢
2. neutral - 中性/客观描述问题
3. dissatisfied - 不满/抱怨/失望
4. angry - 愤怒/指责/激动
5. desperate - 绝望/威胁（要投诉到315、找律师、曝光媒体、再也不用了等）

## 触发词检测：
检查用户是否使用了以下高危触发词：
- "投诉" / "曝光" / "律师" / "315" / "消协" / "再也不用了" / "叫你们经理"
- "退款"+"马上" / "欺骗" / "诈骗" / "假货"

## 情绪趋势评估：
基于历史情绪状态，评估用户情绪是在改善、稳定还是恶化。

## 输出格式（严格JSON）：
{
  "label": "情绪标签",
  "score": 0.0-1.0,
  "triggers": ["检测到的触发词"],
  "trend_assessment": "improving|stable|declining|first_message"
}
只输出JSON，不要任何其他文字。"""


class SentimentAnalyzerAgent(BaseAgent):
    def __init__(self, llm_client: AsyncOpenAI):
        super().__init__("sentiment_analyzer", llm_client)

    async def execute(self, state: AgentState) -> dict[str, Any]:
        messages = state.get("messages", [])
        if not messages:
            return {"sentiment": {"label": "neutral", "score": 0.5, "triggers": [], "trend_assessment": "first_message"}}

        last_msg = messages[-1]
        user_text = message_text(last_msg)

        # Get historical sentiment for trend context
        existing_sentiment = state.get("sentiment")

        try:
            context = f"历史情绪: {json.dumps(existing_sentiment, ensure_ascii=False) if existing_sentiment else '无'}\n\n当前消息: {user_text}"
            raw = await self._call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_message=context,
                model=FAST_MODEL,
                max_tokens=512,
            )
            result = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            sentiment = {
                "label": result.get("label", "neutral"),
                "score": float(result.get("score", 0.5)),
                "triggers": result.get("triggers", []),
                "trend_assessment": result.get("trend_assessment", "stable"),
            }
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}, using fallback")
            sentiment = {"label": "neutral", "score": 0.5, "triggers": [], "trend_assessment": "stable"}

        return {
            "sentiment": sentiment,
            "agent_decisions": [{"agent": "sentiment_analyzer", "decision": sentiment["label"], "score": sentiment["score"]}],
        }
