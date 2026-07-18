"""Ticket Agent — auto-creates and manages tickets from conversation context."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent, message_text
from app.schemas.agent import AgentState
from app.core.llm import FAST_MODEL

logger = logging.getLogger("customer_service.agents.ticket")

SYSTEM_PROMPT = """你是一个专业的工单创建助手。从对话上下文中提取工单所需信息。

## 工单分类：
- order_inquiry → 订单查询类
- refund → 退款退货
- tech_support → 技术支持
- complaint → 投诉
- account → 账户问题
- shipping → 物流配送
- other → 其他

## 优先级规则：
- P0（紧急）：系统故障、安全事件、VIP重大投诉、法律威胁
- P1（高）：支付失败、订单丢失、投诉升级、情绪绝望
- P2（中）：退货问题、物流异常、账户问题
- P3（低）：使用咨询、发票申请、一般FAQ

## SLA计算：
- P0: 响应15分钟 / 解决1小时
- P1: 响应30分钟 / 解决4小时
- P2: 响应1小时 / 解决8小时
- P3: 响应4小时 / 解决24小时

## 输出格式（严格JSON）：
{
  "title": "工单标题（简洁明了，15字以内）",
  "category": "分类",
  "priority": "P0-P3",
  "description": "工单描述（结构化：用户诉求、问题背景、已尝试方案、期望结果）",
  "suggested_dept": "建议处理部门（客服部/技术部/物流部/财务部/法务部）",
  "can_auto_resolve": false
}
只输出JSON，不要任何其他文字。"""

# Department routing by category
CATEGORY_DEPT_MAP = {
    "order_inquiry": "客服部",
    "refund": "客服部",
    "tech_support": "技术部",
    "complaint": "客服部",
    "account": "客服部",
    "shipping": "物流部",
    "payment": "财务部",
    "other": "客服部",
}


class TicketAgent(BaseAgent):
    def __init__(self, llm_client: AsyncOpenAI):
        super().__init__("ticket_agent", llm_client)

    async def execute(self, state: AgentState) -> dict[str, Any]:
        messages = state.get("messages", [])
        if not messages:
            return {"ticket_draft": None}

        # Build conversation context from last few messages
        recent = messages[-6:]  # Last 6 messages (3 exchanges)
        context_parts = []
        for m in recent:
            role = m.get("role", "unknown") if isinstance(m, dict) else "unknown"
            content = m.get("content", "") if isinstance(m, dict) else str(m)
            context_parts.append(f"[{role}]: {content}")

        conversation_context = "\n".join(context_parts)

        # Get enriched context
        intent = state.get("intent", {})
        sentiment = state.get("sentiment", {})
        profile = state.get("profile", {})

        enriched = (
            f"意图: {json.dumps(intent, ensure_ascii=False)}\n"
            f"情绪: {json.dumps(sentiment, ensure_ascii=False)}\n"
            f"用户画像: {json.dumps(profile, ensure_ascii=False)}\n\n"
            f"对话内容:\n{conversation_context}"
        )

        try:
            raw = await self._call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_message=enriched,
                model=FAST_MODEL,
                max_tokens=1024,
            )
            result = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        except Exception as e:
            logger.warning(f"Ticket extraction failed: {e}, using fallback")
            last_msg = message_text(messages[-1])
            result = {
                "title": last_msg[:30],
                "category": intent.get("label", "other") if intent else "other",
                "priority": "P2",
                "description": conversation_context,
                "suggested_dept": "客服部",
                "can_auto_resolve": False,
            }

        ticket_draft = {
            "title": result.get("title", "无标题工单"),
            "category": result.get("category", "other"),
            "priority": self._calc_priority(result, sentiment, profile),
            "description": result.get("description", ""),
            "suggested_dept": result.get("suggested_dept", CATEGORY_DEPT_MAP.get(result.get("category", ""), "客服部")),
        }

        return {
            "ticket_draft": ticket_draft,
            "agent_decisions": [{"agent": "ticket_agent", "decision": f"created:{ticket_draft['priority']}", "category": ticket_draft["category"]}],
        }

    def _calc_priority(self, result: dict, sentiment: dict | None, profile: dict | None) -> str:
        """Calculate final priority considering sentiment and user tier."""
        base_priority = result.get("priority", "P3")

        # Upgrade for strong negative sentiment
        if sentiment:
            label = sentiment.get("label", "")
            triggers = sentiment.get("triggers", [])
            if label == "desperate" or len(triggers) > 0:
                return "P0" if base_priority in ("P1", "P2") else "P1"
            if label == "angry":
                return "P1" if base_priority in ("P2", "P3") else "P0"

        # Upgrade for VIP
        if profile and profile.get("tier") == "vip":
            priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
            upgraded = max(0, priority_order.get(base_priority, 3) - 1)
            for k, v in priority_order.items():
                if v == upgraded:
                    return k

        return base_priority

    @staticmethod
    def calc_sla_deadlines(priority: str) -> tuple[datetime, datetime]:
        """Calculate response and resolution SLA deadlines from now."""
        now = datetime.now(timezone.utc)
        sla_map = {
            "P0": (timedelta(minutes=15), timedelta(hours=1)),
            "P1": (timedelta(minutes=30), timedelta(hours=4)),
            "P2": (timedelta(hours=1), timedelta(hours=8)),
            "P3": (timedelta(hours=4), timedelta(hours=24)),
        }
        resp_delta, resolve_delta = sla_map.get(priority, sla_map["P3"])
        return now + resp_delta, now + resolve_delta
