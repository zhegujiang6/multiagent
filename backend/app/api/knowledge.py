"""Knowledge management API — CRUD for knowledge articles and extraction triggers."""

import uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from app.schemas.knowledge import (
    KnowledgeArticleResponse,
    KnowledgeArticleListResponse,
    ExtractKnowledgeResponse,
    RejectArticleRequest,
    FillGapRequest,
    GapStatsResponse,
    CreateKnowledgeArticleRequest,
    KnowledgeVersionResponse,
    KnowledgeFeedbackRequest,
    KnowledgeFeedbackResponse,
)
from app.services.knowledge_service import (
    get_article,
    list_articles,
    approve_article,
    reject_article,
    delete_article,
    create_knowledge_article,
    list_gaps,
    fill_gap,
    AUTO_APPROVE_CONFIDENCE,
    DRAFT_CONFIDENCE,
    list_versions,
    create_feedback,
)
from app.services.knowledge_extraction_service import extract_knowledge_from_conversation

logger = logging.getLogger("customer_service.api.knowledge")
router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


# ── List Articles ──

@router.post("/articles", response_model=KnowledgeArticleResponse, status_code=201)
async def create_manual_knowledge_article(body: CreateKnowledgeArticleRequest):
    """Create a governed manual knowledge draft."""
    article = await create_knowledge_article(
        title=body.title,
        content=body.content,
        category=body.category,
        tags=body.tags,
        status="draft",
        source_type="manual",
        owner=body.owner,
    )
    return KnowledgeArticleResponse.model_validate(article)

@router.get("/articles", response_model=KnowledgeArticleListResponse)
async def list_knowledge_articles(
    status: str | None = Query(None, description="Filter by status: draft, approved, rejected"),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List knowledge articles with optional filters and pagination."""
    articles, total = await list_articles(
        status=status,
        category=category,
        page=page,
        page_size=page_size,
    )
    return KnowledgeArticleListResponse(
        articles=[KnowledgeArticleResponse.model_validate(a) for a in articles],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Get Single Article ──

@router.get("/articles/{article_id}", response_model=KnowledgeArticleResponse)
async def get_knowledge_article(article_id: uuid.UUID):
    """Get a single knowledge article by ID."""
    article = await get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Knowledge article not found")
    return KnowledgeArticleResponse.model_validate(article)


@router.get("/articles/{article_id}/versions", response_model=list[KnowledgeVersionResponse])
async def get_knowledge_article_versions(article_id: uuid.UUID):
    """List immutable versions for audit and rollback planning."""
    article = await get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Knowledge article not found")
    versions = await list_versions(article_id)
    return [KnowledgeVersionResponse.model_validate(version) for version in versions]


# ── Approve Article ──

@router.post("/articles/{article_id}/approve", response_model=KnowledgeArticleResponse)
async def approve_knowledge_article(article_id: uuid.UUID):
    """Approve a draft article — publishes it to Qdrant."""
    try:
        article = await approve_article(article_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Approve article failed: {e}")
        raise HTTPException(status_code=500, detail=f"Approval failed: {e}")
    return KnowledgeArticleResponse.model_validate(article)


# ── Reject Article ──

@router.post("/articles/{article_id}/reject", response_model=KnowledgeArticleResponse)
async def reject_knowledge_article(article_id: uuid.UUID, body: RejectArticleRequest = RejectArticleRequest()):
    """Reject a draft article."""
    try:
        article = await reject_article(article_id, reason=body.reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return KnowledgeArticleResponse.model_validate(article)


# ── Delete Article ──

@router.delete("/articles/{article_id}")
async def delete_knowledge_article(article_id: uuid.UUID):
    """Delete an article from PostgreSQL and Qdrant."""
    try:
        await delete_article(article_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "deleted", "article_id": str(article_id)}


# ── Extract Knowledge from Conversation ──

@router.post("/extract/{conversation_id}", response_model=ExtractKnowledgeResponse)
async def extract_knowledge(conversation_id: str):
    """Extract Q&A pairs from a conversation using LLM (does NOT save)."""
    pairs = await extract_knowledge_from_conversation(conversation_id)
    return ExtractKnowledgeResponse(
        conversation_id=conversation_id,
        extracted_pairs=pairs,
        saved_count=0,
    )


# ── Extract and Auto-Save ──

@router.post("/extract/{conversation_id}/save", response_model=ExtractKnowledgeResponse)
async def extract_and_save_knowledge(conversation_id: str):
    """Extract Q&A pairs from a conversation and auto-save with confidence-based routing.

    Self-evolution pipeline:
      - confidence >= {AUTO} → auto-approved + published to Qdrant
      - confidence >= {DRAFT} → saved as draft for human review
      - confidence <  {DRAFT} → discarded
    """.format(AUTO=AUTO_APPROVE_CONFIDENCE, DRAFT=DRAFT_CONFIDENCE)
    from app.services.knowledge_service import auto_approve_article, delete_article as del_article

    pairs = await extract_knowledge_from_conversation(conversation_id)

    auto_approved = 0
    drafted = 0
    discarded = 0
    errors = []

    for pair in pairs:
        confidence = pair.get("confidence", 0.5)
        try:
            content = f"问题：{pair['question']}\n\n答案：{pair['answer']}"
            article = await create_knowledge_article(
                title=pair["title"],
                content=content,
                category=pair.get("category", "other"),
                tags=pair.get("tags", []),
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
                await del_article(article.id)
                discarded += 1
        except Exception as e:
            errors.append({"title": pair.get("title", ""), "error": str(e)})
            logger.warning(f"Failed to save extracted pair: {e}")

    return ExtractKnowledgeResponse(
        conversation_id=conversation_id,
        extracted_pairs=pairs,
        saved_count=auto_approved + drafted,
        auto_approved_count=auto_approved,
        drafted_count=drafted,
        discarded_count=discarded,
    )


# ═══════════════════════════════════════════════════════════
#  Self-Evolution Endpoints: Gaps & Stats
# ═══════════════════════════════════════════════════════════


@router.get("/gaps", response_model=KnowledgeArticleListResponse)
async def list_knowledge_gaps(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all knowledge gaps — queries where RAG failed to find an answer.

    These are waiting for human experts to fill with content.
    """
    gaps, total = await list_gaps(page=page, page_size=page_size)
    return KnowledgeArticleListResponse(
        articles=[KnowledgeArticleResponse.model_validate(g) for g in gaps],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/gaps/{gap_id}/fill", response_model=KnowledgeArticleResponse)
async def fill_knowledge_gap(gap_id: uuid.UUID, body: FillGapRequest):
    """Fill a knowledge gap with expert content — auto-publishes to Qdrant."""
    try:
        article = await fill_gap(
            gap_id=gap_id,
            content=body.content,
            category=body.category,
            tags=body.tags,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Fill gap failed: {e}")
        raise HTTPException(status_code=500, detail=f"Fill gap failed: {e}")
    return KnowledgeArticleResponse.model_validate(article)


@router.post("/feedback", response_model=KnowledgeFeedbackResponse, status_code=201)
async def submit_knowledge_feedback(body: KnowledgeFeedbackRequest):
    """Capture explicit user or operator feedback for knowledge quality scoring."""
    feedback = await create_feedback(
        retrieval_event_id=body.retrieval_event_id,
        conversation_id=body.conversation_id,
        article_id=body.article_id,
        feedback_type=body.feedback_type,
        score=body.score,
        comment=body.comment,
        source=body.source,
    )
    if body.conversation_id:
        from app.services.memory_service import record_satisfaction_feedback
        await record_satisfaction_feedback(str(body.conversation_id), body.feedback_type)
    return KnowledgeFeedbackResponse.model_validate(feedback)


@router.get("/stats", response_model=GapStatsResponse)
async def get_knowledge_stats():
    """Get self-evolution dashboard stats."""
    from app.models.knowledge import (
        KnowledgeArticle,
        KnowledgeArticleVersion,
        KnowledgeChunk,
        KnowledgeFeedback,
        RetrievalEvent,
    )
    from app.core.database import async_session_factory
    from sqlalchemy import select, func

    async with async_session_factory() as session:
        # Total gaps
        gap_count = await session.scalar(
            select(func.count(KnowledgeArticle.id)).where(
                KnowledgeArticle.status == "gap"
            )
        ) or 0

        # Total articles (excluding gaps)
        total_articles = await session.scalar(
            select(func.count(KnowledgeArticle.id)).where(
                KnowledgeArticle.status != "gap"
            )
        ) or 0

        # Approved
        approved = await session.scalar(
            select(func.count(KnowledgeArticle.id)).where(
                KnowledgeArticle.status == "approved"
            )
        ) or 0

        # Drafts
        drafts = await session.scalar(
            select(func.count(KnowledgeArticle.id)).where(
                KnowledgeArticle.status == "draft"
            )
        ) or 0

        rejected = await session.scalar(
            select(func.count(KnowledgeArticle.id)).where(
                KnowledgeArticle.status == "rejected"
            )
        ) or 0
        total_versions = await session.scalar(select(func.count(KnowledgeArticleVersion.id))) or 0
        total_chunks = await session.scalar(select(func.count(KnowledgeChunk.id))) or 0

        since = datetime.now(timezone.utc) - timedelta(hours=24)
        retrievals_24h = await session.scalar(
            select(func.count(RetrievalEvent.id)).where(RetrievalEvent.created_at >= since)
        ) or 0
        answered_24h = await session.scalar(
            select(func.count(RetrievalEvent.id)).where(
                RetrievalEvent.created_at >= since,
                RetrievalEvent.answered.is_(True),
            )
        ) or 0
        feedback_count = await session.scalar(select(func.count(KnowledgeFeedback.id))) or 0
        positive_feedback = await session.scalar(
            select(func.count(KnowledgeFeedback.id)).where(
                KnowledgeFeedback.feedback_type.in_(("helpful", "resolved"))
            )
        ) or 0

        # Average effectiveness
        avg_eff = await session.scalar(
            select(func.avg(KnowledgeArticle.effectiveness_score)).where(
                KnowledgeArticle.usage_count > 0
            )
        )

    return GapStatsResponse(
        total_gaps=gap_count,
        total_articles=total_articles,
        total_approved=approved,
        total_drafts=drafts,
        total_rejected=rejected,
        total_versions=total_versions,
        total_chunks=total_chunks,
        retrievals_24h=retrievals_24h,
        answered_retrievals_24h=answered_24h,
        feedback_count=feedback_count,
        helpful_rate=round(positive_feedback / feedback_count, 4) if feedback_count else 0.0,
        avg_effectiveness=round(float(avg_eff or 0), 4),
    )
