"""Knowledge closed-loop work triggered by conversation and ticket events."""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger("customer_service.services.knowledge_lifecycle")


async def auto_extract_knowledge(
    ticket_id: str | None,
    conversation_id: str,
) -> None:
    """Extract and persist reusable knowledge after a resolved interaction."""
    try:
        from app.services.knowledge_extraction_service import (
            extract_knowledge_from_conversation,
        )
        from app.services.knowledge_service import (
            AUTO_APPROVE_CONFIDENCE,
            DRAFT_CONFIDENCE,
            auto_approve_article,
            create_knowledge_article,
            delete_article,
        )

        pairs = await extract_knowledge_from_conversation(conversation_id)
        auto_approved = 0
        drafted = 0
        discarded = 0

        for pair in pairs:
            confidence = pair.get("confidence", 0.5)
            content = f"问题：{pair['question']}\n\n答案：{pair['answer']}"
            article = await create_knowledge_article(
                title=pair["title"],
                content=content,
                category=pair.get("category", "other"),
                tags=pair.get("tags", []),
                source_ticket_id=ticket_id,
                source_conversation_id=uuid.UUID(conversation_id),
                status="draft",
                meta_info={
                    "question": pair["question"],
                    "confidence": confidence,
                },
            )

            if confidence >= AUTO_APPROVE_CONFIDENCE:
                await auto_approve_article(article.id)
                auto_approved += 1
            elif confidence >= DRAFT_CONFIDENCE:
                drafted += 1
            else:
                await delete_article(article.id)
                discarded += 1

        if auto_approved or drafted:
            logger.info(
                "[Self-Evolution] Ticket %s: auto-approved=%s, drafted=%s, "
                "discarded=%s",
                ticket_id,
                auto_approved,
                drafted,
                discarded,
            )
    except Exception as exc:
        logger.warning(
            "Auto-extraction failed for ticket %s: %s (non-fatal)",
            ticket_id,
            exc,
        )
