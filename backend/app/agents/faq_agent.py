"""FAQ Agent — RAG-based question answering with knowledge synthesis.

Self-evolution hooks:
  - Knowledge gap detection: when retrieval fails (all scores < threshold),
    a gap record is created for human experts to fill.
  - Usage tracking: when knowledge is successfully used, usage_count and
    effectiveness_score are updated on the source articles.
"""

import asyncio
import json
import logging
import time
from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent, message_text
from app.schemas.agent import AgentState
from app.rag.retriever import multi_path_retrieve, build_knowledge_context

logger = logging.getLogger("customer_service.agents.faq")

# Low-scoring semantic matches are not reliable enough to present as answers.
MIN_ANSWER_SCORE = 0.5

SYSTEM_PROMPT = """你是一个专业的客服问答助手。根据提供的知识库内容回答用户问题。

## 回答原则：
1. 优先使用知识库内容，准确引用信息
2. 如果知识库内容足以回答问题，给出清晰完整的答案，并在末尾标注【参考来源：知识{编号}】
3. 如果知识库内容不足，诚实说明"我查到的信息有限，建议咨询人工客服获取更准确的答复"
4. 回答要简洁、有条理，使用友好专业的语气
5. 对于操作步骤类问题，用1) 2) 3)编号分步说明
6. 根据用户的会员等级调整回答风格（VIP用户更详细、更主动提供服务）

## 输出格式（严格JSON）：
{
  "answer": "完整的回答文本（markdown格式）",
  "sources": ["引用的知识编号"],
  "confidence": 0.0-1.0,
  "needs_escalation": false
}
只输出JSON，不要任何其他文字。"""


class FAQAgent(BaseAgent):
    def __init__(self, llm_client: AsyncOpenAI):
        super().__init__("faq_agent", llm_client)

    async def execute(self, state: AgentState) -> dict[str, Any]:
        """Execute FAQ agent: retrieve → generate → track usage or log gap."""
        messages = state.get("messages", [])
        if not messages:
            return {"response": "您好，请问有什么可以帮助您的？", "retrieved_knowledge": []}

        last_msg = messages[-1]
        user_text = message_text(last_msg)

        intent = state.get("intent", {})
        intent_label = intent.get("label", "") if intent else ""
        conversation_id = state.get("conversation_id", "")

        # Determine which collections to search based on intent
        search_sop = intent_label in ("refund", "complaint", "order_modify")
        search_resolutions = intent_label in ("tech_support", "complaint")

        # Retrieve knowledge
        retrieval_started = time.monotonic()
        try:
            knowledge_results = await multi_path_retrieve(
                user_text,
                top_k=5,
                search_sop=search_sop,
                search_resolutions=search_resolutions,
            )
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            knowledge_results = []

        # ── Self-Evolution: Knowledge Gap Detection ──
        best_score = knowledge_results[0]["score"] if knowledge_results else 0.0
        retrieval_event_id = None
        try:
            from app.services.knowledge_service import record_retrieval_event
            retrieval_event = await record_retrieval_event(
                conversation_id=conversation_id or None,
                query=user_text,
                rewritten_query=None,
                intent=intent_label or None,
                results=knowledge_results,
                latency_ms=int((time.monotonic() - retrieval_started) * 1000),
                answered=bool(knowledge_results and best_score >= MIN_ANSWER_SCORE),
            )
            retrieval_event_id = str(retrieval_event.id)
        except Exception as e:
            logger.warning(f"Retrieval event logging failed: {e}")

        if not knowledge_results or best_score < MIN_ANSWER_SCORE:
            asyncio.create_task(self._log_gap(
                query=user_text,
                intent_label=intent_label,
                conversation_id=conversation_id,
                top_score=best_score,
            ))

        if not knowledge_results or best_score < MIN_ANSWER_SCORE:
            return {
                "retrieved_knowledge": [],
                "knowledge_gap_detected": True,
                "retrieval_event_id": retrieval_event_id,
                "response": "抱歉，我暂时没有找到足够相关的知识库信息。请告诉我更多细节（例如订单号、商品名称或遇到的具体问题），我会继续帮您处理。",
            }

        # Build context and generate answer
        knowledge_context = build_knowledge_context(knowledge_results)
        profile = state.get("profile", {})
        tier = profile.get("tier", "standard") if profile else "standard"
        context = f"用户类型: {tier}\n\n知识库:\n{knowledge_context}\n\n用户问题: {user_text}"

        try:
            raw = await self._call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_message=context,
                max_tokens=1024,
            )
            result = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            answer = result.get("answer", "抱歉，我暂时无法回答这个问题。")
            confidence = float(result.get("confidence", 0.5))
            needs_escalation = result.get("needs_escalation", False)
        except Exception as e:
            logger.warning(f"FAQ answer generation failed: {e}")
            # Fallback: use raw knowledge content
            top = knowledge_results[0]
            answer = f"根据知识库中的信息：\n\n{top['content']}\n\n【参考来源：{top['title']} | 相关度：{top['score']}】"
            confidence = top["score"]
            needs_escalation = confidence < 0.5

        # ── Self-Evolution: Track Knowledge Usage ──
        source_ids = [r["id"] for r in knowledge_results if r.get("id")]
        if source_ids:
            asyncio.create_task(self._track_usage(source_ids))

        return {
            "retrieved_knowledge": knowledge_results,
            "knowledge_source_ids": source_ids,
            "retrieval_event_id": retrieval_event_id,
            "response": answer,
            "should_escalate": needs_escalation,
            "agent_decisions": [{"agent": "faq_agent", "decision": "answered", "confidence": confidence, "sources_count": len(knowledge_results)}],
        }

    # ── Self-Evolution Helpers ──

    async def _log_gap(
        self,
        query: str,
        intent_label: str,
        conversation_id: str,
        top_score: float,
    ) -> None:
        """Background: record a knowledge gap for human review."""
        try:
            import uuid as _uuid
            from app.services.knowledge_service import create_gap_record

            cid = _uuid.UUID(conversation_id) if conversation_id else None
            await create_gap_record(
                query=query,
                intent_label=intent_label,
                conversation_id=cid,
                top_retrieval_score=top_score,
            )
        except Exception as e:
            logger.debug(f"[Self-Evolution] Gap logging skipped: {e}")

    async def _track_usage(self, source_ids: list[str]) -> None:
        """Background: increment usage counters on source articles."""
        try:
            from app.services.knowledge_service import track_knowledge_usage
            await track_knowledge_usage(source_ids)
        except Exception as e:
            logger.debug(f"[Self-Evolution] Usage tracking skipped: {e}")
