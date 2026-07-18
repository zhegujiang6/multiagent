"""Intent Classifier Agent — classifies user intent from conversation text."""

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent, message_text
from app.schemas.agent import AgentState
from app.core.llm import FAST_MODEL

logger = logging.getLogger("customer_service.agents.intent")

SYSTEM_PROMPT = """你是一个专业的客服意图分类器。分析用户消息，输出JSON格式的分类结果。

## 意图标签（12类）：
1. faq - 常见问题咨询（退换货政策、配送时效、使用说明等）
2. product_info - 产品信息查询（规格、价格、库存、对比）
3. order_inquiry - 订单查询（订单状态、物流进度）
4. order_modify - 订单修改（修改地址、取消订单、改配送方式）
5. refund - 退款退货（申请退款、退货进度、退款到账）
6. tech_support - 技术支持（App故障、网站问题、使用问题）
7. complaint - 投诉（服务投诉、商品投诉、投诉升级）
8. account - 账户问题（登录、密码、绑定、注销）
9. payment - 支付问题（支付失败、发票、优惠券）
10. shipping - 物流配送（运费、配送方式、时效）
11. membership - 会员相关（VIP权益、升级、积分）
12. chitchat - 闲聊/问候/无明确意图
13. other - 其他未分类

## 实体提取：
提取用户消息中的关键实体：订单号、商品名、金额、日期、快递公司、地址等。

## 输出格式（严格JSON）：
{
  "label": "意图标签",
  "confidence": 0.0-1.0,
  "entities": [{"name": "实体名", "value": "实体值"}],
  "sub_intents": ["次要意图"],
  "is_ambiguous": false
}
只输出JSON，不要任何其他文字。"""


class IntentClassifierAgent(BaseAgent):
    def __init__(self, llm_client: AsyncOpenAI):
        super().__init__("intent_classifier", llm_client)

    async def execute(self, state: AgentState) -> dict[str, Any]:
        # Get the last user message
        messages = state.get("messages", [])
        if not messages:
            return {"intent": {"label": "chitchat", "confidence": 1.0, "entities": [], "sub_intents": []}}

        last_msg = messages[-1]
        user_text = message_text(last_msg)

        try:
            raw = await self._call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_text,
                model=FAST_MODEL,
                max_tokens=512,
            )
            result = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            intent = {
                "label": result.get("label", "other"),
                "confidence": float(result.get("confidence", 0.5)),
                "entities": result.get("entities", []),
                "sub_intents": result.get("sub_intents", []),
            }
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}, using fallback")
            intent = {"label": "faq", "confidence": 0.3, "entities": [], "sub_intents": []}

        return {
            "intent": intent,
            "agent_decisions": [{"agent": "intent_classifier", "decision": intent["label"], "confidence": intent["confidence"]}],
        }
