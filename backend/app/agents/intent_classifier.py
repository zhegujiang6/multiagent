"""Intent Classifier Agent — classifies user intent from conversation text."""

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent, message_text
from app.schemas.agent import AgentState
from app.core.llm import FAST_MODEL

logger = logging.getLogger("customer_service.agents.intent")

INTENT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("complaint", ("投诉", "315", "消协", "律师", "曝光", "欺诈", "假货")),
    ("refund", ("退款", "退货", "退钱", "refund")),
    ("order_modify", ("取消订单", "修改订单", "修改地址", "改地址", "改配送")),
    ("payment", ("支付失败", "支付", "扣款", "发票", "优惠券")),
    ("shipping", ("物流", "快递", "配送", "运费", "没收到货", "未收到货")),
    ("tech_support", ("报错", "故障", "崩溃", "打不开", "无法打开", "系统繁忙", "技术支持")),
    ("account", ("登录", "密码", "账号", "账户", "绑定", "注销")),
    ("membership", ("会员", "vip", "积分")),
    ("product_info", ("商品", "产品", "库存", "价格", "规格")),
    ("order_inquiry", ("订单", "订单号", "查单")),
    ("chitchat", ("你好", "您好", "hello", "hi", "hey")),
)

ORDER_ID_PATTERN = re.compile(
    r"(?:订单号|order(?:\s*id)?)\s*[：:#-]?\s*([a-z0-9][a-z0-9_-]{3,})",
    re.IGNORECASE,
)


def classify_intent_with_rules(user_text: str) -> dict[str, Any]:
    """Provide a useful deterministic fallback when the LLM is unavailable."""
    normalized = user_text.strip().lower()
    label = "faq"
    confidence = 0.3

    for candidate, keywords in INTENT_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            label = candidate
            confidence = 0.85
            break

    entities: list[dict[str, str]] = []
    order_match = ORDER_ID_PATTERN.search(normalized)
    if order_match:
        entities.append({"name": "order_id", "value": order_match.group(1)})

    return {
        "label": label,
        "confidence": confidence,
        "entities": entities,
        "sub_intents": [],
    }

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
        memory_context = state.get("memory_context", "")
        prompt_input = (
            f"{memory_context}\n\n当前用户消息：{user_text}"
            if memory_context
            else user_text
        )

        try:
            raw = await self._call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_message=prompt_input,
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
            intent = classify_intent_with_rules(user_text)

        return {
            "intent": intent,
            "agent_decisions": [{"agent": "intent_classifier", "decision": intent["label"], "confidence": intent["confidence"]}],
        }
