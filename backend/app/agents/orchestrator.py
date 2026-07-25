"""Orchestrator Agent — LangGraph StateGraph that coordinates all sub-agents.

This is the central nervous system of the Multi-Agent architecture.
It defines the state machine that routes messages through the appropriate agents.
"""

import asyncio
import json
import logging
from typing import Any, Literal

from langgraph.graph import StateGraph, END
from openai import AsyncOpenAI

from app.schemas.agent import AgentState
from app.agents.base import BaseAgent, message_text
from app.agents.registry import AgentRegistry
from app.core.llm import DEFAULT_MODEL, FAST_MODEL
from app.clients.java_ticket_client import get_java_ticket_client

logger = logging.getLogger("customer_service.agent.orchestrator")

GREETING_MESSAGES = {
    "你好", "您好", "嗨", "哈喽", "在吗", "在不在", "早上好", "下午好", "晚上好",
    "hello", "hi", "hey",
}

# ── Routing Decision Prompts ──

ROUTING_SYSTEM_PROMPT = """你是一个客服路由决策器。根据意图分析、情绪分析和用户画像，决定下一步行动。

## 可选路由：
1. faq_answer — FAQ自动回答（知识库能解决的问题）
2. create_ticket — 创建工单（需要人工或跨部门处理）
3. escalate_to_human — 转接人工（用户要求、情绪激动、复杂投诉）
4. direct_response — 直接回复（简单问候、闲聊、感谢）

## 决策规则：
- 情绪为angry/desperate → escalate_to_human
- 意图为complaint + 有法律威胁触发词 → escalate_to_human
- 意图为faq/product_info/account/chitchat → faq_answer
- 意图为refund/order_inquiry/tech_support/shipping → create_ticket
- 用户明确说"转人工"/"叫你们经理" → escalate_to_human
- 简单问候/感谢 → direct_response

## 输出格式（严格JSON）：
{
  "route": "路由选择",
  "reason": "决策理由（一句话）"
}
只输出JSON。"""


class OrchestratorAgent(BaseAgent):
    """The master orchestrator that manages the full agent pipeline."""

    def __init__(self, llm_client: AsyncOpenAI, registry: AgentRegistry):
        super().__init__("orchestrator", llm_client)
        self.registry = registry
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph with all agent nodes."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("parallel_preprocess", self._parallel_preprocess_node)
        workflow.add_node("enrich_profile", self._enrich_profile_node)
        workflow.add_node("route", self._route_node)
        workflow.add_node("faq_answer", self._faq_answer_node)
        workflow.add_node("create_ticket", self._create_ticket_node)
        workflow.add_node("escalate_to_human", self._escalate_node)
        workflow.add_node("direct_response", self._direct_response_node)
        workflow.add_node("synthesize_response", self._synthesize_response_node)

        # Define edges
        workflow.set_entry_point("parallel_preprocess")
        workflow.add_edge("parallel_preprocess", "enrich_profile")
        workflow.add_edge("enrich_profile", "route")

        workflow.add_conditional_edges(
            "route",
            self._route_decision_fn,
            {
                "faq_answer": "faq_answer",
                "create_ticket": "create_ticket",
                "escalate_to_human": "escalate_to_human",
                "direct_response": "direct_response",
            },
        )

        # All leaf nodes converge to synthesize
        workflow.add_edge("faq_answer", "synthesize_response")
        workflow.add_edge("create_ticket", "synthesize_response")
        workflow.add_edge("escalate_to_human", "synthesize_response")
        workflow.add_edge("direct_response", "synthesize_response")
        workflow.add_edge("synthesize_response", END)

        return workflow.compile()

    # ── Graph Nodes ──

    async def _parallel_preprocess_node(self, state: AgentState) -> dict[str, Any]:
        """Run Intent Classifier and Sentiment Analyzer in parallel.

        Skips LLM calls if intent/sentiment were already populated by the
        streaming layer (process_message_streaming pre-runs them for status
        updates before the orchestrator runs).
        """
        existing_intent = state.get("intent")
        existing_sentiment = state.get("sentiment")

        if existing_intent and existing_sentiment:
            logger.info("[Orchestrator] Preprocess already done by streaming layer, skipping")
            return {}

        logger.info("[Orchestrator] Starting parallel preprocessing...")

        intent_agent = self.registry.get("intent_classifier")
        sentiment_agent = self.registry.get("sentiment_analyzer")

        intent_result, sentiment_result = await asyncio.gather(
            intent_agent.execute(state),
            sentiment_agent.execute(state),
        )

        merged: dict[str, Any] = {}
        merged.update(intent_result)
        merged.update(sentiment_result)
        return merged

    async def _enrich_profile_node(self, state: AgentState) -> dict[str, Any]:
        """Enrich user profile.

        Skips if profile was already populated by the streaming layer
        (process_message_streaming pre-runs it for status updates).
        """
        existing_profile = state.get("profile")
        if existing_profile:
            logger.info("[Orchestrator] Profile already enriched by streaming layer, skipping")
            return {}

        logger.info("[Orchestrator] Enriching profile...")
        profile_agent = self.registry.get("profile_enricher")
        return await profile_agent.execute(state)

    async def _route_node(self, state: AgentState) -> dict[str, Any]:
        """Route to the best handling path."""
        intent = state.get("intent", {})
        sentiment = state.get("sentiment", {})

        messages = state.get("messages", [])
        last_message = messages[-1] if messages else {}
        user_text = message_text(last_message)
        normalized_text = user_text.strip().lower()

        if any(
            phrase in normalized_text
            for phrase in ("创建工单", "新建工单", "提交工单", "生成工单")
        ):
            return {
                "agent_decisions": [{
                    "agent": "orchestrator",
                    "decision": "create_ticket",
                    "reason": "user explicitly requested a ticket",
                    "route": "routing",
                }],
            }

        if any(
            phrase in normalized_text
            for phrase in ("转人工", "人工客服", "找客服", "找人工", "联系人工")
        ):
            return {
                "agent_decisions": [{
                    "agent": "orchestrator",
                    "decision": "escalate_to_human",
                    "reason": "user explicitly requested a human agent",
                    "route": "routing",
                }],
            }

        if user_text.strip().lower().rstrip("!！。.?？") in GREETING_MESSAGES:
            return {
                "agent_decisions": [{
                    "agent": "orchestrator",
                    "decision": "direct_response",
                    "reason": "short greeting",
                    "route": "routing",
                }],
            }

        # Build routing context
        context = json.dumps({
            "intent": intent,
            "sentiment": sentiment,
            "session_memory": state.get("session_memory", {}),
            "user_memory": state.get("user_memory", {}),
        }, ensure_ascii=False)

        try:
            raw = await self._call_llm(
                system_prompt=ROUTING_SYSTEM_PROMPT,
                user_message=context,
                model=FAST_MODEL,
                max_tokens=256,
            )
            result = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            route = result.get("route", "faq_answer")
            reason = result.get("reason", "")
        except Exception:
            # Fallback routing logic
            route, reason = self._fallback_route(intent, sentiment)

        logger.info(f"[Orchestrator] Routing: {route} — {reason}")
        return {
            "agent_decisions": [{"agent": "orchestrator", "decision": route, "reason": reason, "route": "routing"}],
        }

    def _fallback_route(self, intent: dict | None, sentiment: dict | None) -> tuple[str, str]:
        """Rule-based fallback when LLM routing fails."""
        if sentiment:
            label = sentiment.get("label", "")
            triggers = sentiment.get("triggers", [])
            if label in ("angry", "desperate") or len(triggers) > 0:
                return "escalate_to_human", "检测到负面情绪或触发词"

        if intent:
            label = intent.get("label", "")
            if label == "complaint":
                return "escalate_to_human", "投诉类问题需人工处理"
            if label in ("faq", "product_info", "account", "chitchat", "membership"):
                return "faq_answer", "知识库可覆盖的问题"
            if label in ("refund", "order_inquiry", "order_modify", "tech_support", "shipping", "payment"):
                return "create_ticket", "需要创建工单跟进"

        return "faq_answer", "默认FAQ路径"

    async def _faq_answer_node(self, state: AgentState) -> dict[str, Any]:
        """Answer via FAQ/RAG."""
        logger.info("[Orchestrator] FAQ answer path...")
        faq_agent = self.registry.get("faq_agent")
        return await faq_agent.execute(state)

    async def _create_ticket_node(self, state: AgentState) -> dict[str, Any]:
        """Create a ticket and generate a user-friendly response."""
        logger.info("[Orchestrator] Creating ticket...")
        ticket_agent = self.registry.get("ticket_agent")
        result = await ticket_agent.execute(state)

        draft = result.get("ticket_draft", {})
        priority = draft.get("priority", "P3")
        category = draft.get("category", "other")
        title = draft.get("title", "您的问题")

        priority_map = {
            "P0": "URGENT",
            "P1": "HIGH",
            "P2": "MEDIUM",
            "P3": "LOW",
        }
        ticket = await get_java_ticket_client().create_ticket(
            request_id=state.get("request_id") or f"conv-{state.get('conversation_id')}",
            conversation_id=state.get("conversation_id", "unknown"),
            user_id=state.get("customer_id", "anonymous"),
            category=str(category).upper(),
            priority=priority_map.get(priority, "LOW"),
            summary=draft.get("description") or title,
        )
        result["ticket_id"] = str(ticket["ticketId"])
        result["ticket"] = ticket

        # SLA estimates
        sla_map = {"P0": "1小时内", "P1": "4小时内", "P2": "8小时内", "P3": "24小时内"}
        sla_text = sla_map.get(priority, "24小时内")

        result["response"] = (
            f"我已收到您的问题「{title}」，并为您创建了工单进行跟进。\n\n"
            f"📋 **工单信息**\n"
            f"- 工单号：{ticket['ticketId']}\n"
            f"- 优先级：{priority}\n"
            f"- 分类：{category}\n"
            f"- 预计处理时间：{sla_text}\n\n"
            f"我们的客服团队会尽快为您处理，您可以在「我的工单」中随时查看进度。"
            f"如有任何补充信息，请随时告诉我。"
        )

        return result

    async def _escalate_node(self, state: AgentState) -> dict[str, Any]:
        """Escalate to human agent."""
        logger.info("[Orchestrator] Escalating to human...")
        return {
            "should_escalate": True,
            "response": (
                "您的咨询已升级为人工服务。我已经为您生成了问题摘要，"
                "专业客服人员正在赶来，预计等待时间不超过30秒。\n\n"
                "在此期间，您可以继续描述您的问题，我会全程协助。"
            ),
            "agent_decisions": [{"agent": "orchestrator", "decision": "escalate_to_human", "route": "escalation"}],
        }

    async def _direct_response_node(self, state: AgentState) -> dict[str, Any]:
        """Handle simple greetings/chitchat directly."""
        messages = state.get("messages", [])
        last_msg = message_text(messages[-1]) if messages else ""

        response = (
            "您好！我是智能客服助手，请问有什么可以帮助您的吗？"
            "无论您想查询订单、申请退款、了解产品，还是遇到任何问题，"
            "我都很乐意为您服务！"
        )
        return {
            "response": response,
            "agent_decisions": [{"agent": "orchestrator", "decision": "direct_response", "route": "direct"}],
        }

    async def _synthesize_response_node(self, state: AgentState) -> dict[str, Any]:
        """Final synthesis — polish the response with empathy and formatting."""
        response = state.get("response", "")
        sentiment = state.get("sentiment", {})
        profile = state.get("profile", {})

        if not response:
            return {}

        # Add empathy prefix for negative sentiment
        empathy_prefix = ""
        if sentiment:
            label = sentiment.get("label", "")
            if label == "angry":
                empathy_prefix = "非常理解您的心情，给您带来不好的体验我们深表歉意。"
            elif label == "dissatisfied":
                empathy_prefix = "很抱歉给您带来不便，让我来帮您处理。"
            elif label == "desperate":
                empathy_prefix = "您的问题我们已经高度重视，我将立即为您升级处理。"

        if empathy_prefix and not response.startswith(empathy_prefix):
            response = empathy_prefix + "\n\n" + response

        # Add VIP touch
        if profile and profile.get("tier") == "vip":
            response += "\n\n💎 作为我们的VIP会员，您的问题享有最高优先级服务。如有任何不满意，请随时告诉我。"

        return {"response": response}

    # ── Conditional Edge Function ──

    def _route_decision_fn(self, state: AgentState) -> Literal["faq_answer", "create_ticket", "escalate_to_human", "direct_response"]:
        """Extract routing decision from state for LangGraph conditional edges."""
        # Check if any agent set escalation
        if state.get("should_escalate"):
            return "escalate_to_human"

        # Get route from agent_decisions
        decisions = state.get("agent_decisions", [])
        for d in reversed(decisions):
            if d.get("agent") == "orchestrator" and d.get("route") == "routing":
                decision = d.get("decision", "")
                if decision in ("faq_answer", "create_ticket", "escalate_to_human", "direct_response"):
                    return decision  # type: ignore[return-value]

        return "faq_answer"

    async def execute(self, state: AgentState) -> dict[str, Any]:
        """Execute the full agent pipeline (required by BaseAgent ABC)."""
        result = await self.run(state)
        return dict(result)

    # ── Public API ──

    async def run(self, state: AgentState, timeout: float = 25.0) -> AgentState:
        """Execute the full agent pipeline and return the final state.

        Args:
            timeout: Max seconds for the entire pipeline (default 25s).
                     Pipeline: parallel agents → route → leaf agent → synthesize.
                     Normal: ~8-12s, 25s is generous headroom.
        """
        logger.info(f"[Orchestrator] Running pipeline for conversation: {state.get('conversation_id', 'unknown')}")
        try:
            final_state = await asyncio.wait_for(
                self.graph.ainvoke(state),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error(f"[Orchestrator] Pipeline timed out after {timeout}s — falling back to escalation")
            # Return a fallback state so the user gets a response
            return {
                "response": "抱歉，系统处理您的请求时超时了，正在为您转接人工客服，请稍候...",
                "should_escalate": True,
                "error": f"Pipeline timeout after {timeout}s",
            }
        return final_state
