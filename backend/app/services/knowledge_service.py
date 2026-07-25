"""Knowledge asset service: governance, versioning, vector sync and feedback."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.models.knowledge import (
    KnowledgeArticle,
    KnowledgeArticleVersion,
    KnowledgeChunk,
    KnowledgeFeedback,
    RetrievalEvent,
)
from app.rag.vector_store import (
    FAQ_COLLECTION,
    SOP_COLLECTION,
    delete_documents,
    upsert_documents,
)

logger = logging.getLogger("customer_service.services.knowledge")

AUTO_APPROVE_CONFIDENCE = 0.8
DRAFT_CONFIDENCE = 0.6
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def content_hash(title: str, content: str) -> str:
    return hashlib.sha256(f"{title.strip()}\n{content.strip()}".encode("utf-8")).hexdigest()


def _canonical_key(
    *,
    title: str,
    content: str,
    source_type: str,
    source_ticket_id: str | None,
    source_conversation_id: uuid.UUID | None,
) -> str:
    if source_ticket_id:
        prefix = f"ticket:{source_ticket_id}"
    elif source_conversation_id:
        prefix = f"conversation:{source_conversation_id}"
    else:
        prefix = source_type
    return f"{prefix}:{content_hash(title, content)[:32]}"


def _split_content(content: str) -> list[str]:
    text = content.strip()
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = max(text.rfind("。", start, end), text.rfind("\n", start, end))
            if boundary > start + CHUNK_SIZE // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return [chunk for chunk in chunks if chunk]


def _collection_for(article: KnowledgeArticle) -> str:
    return SOP_COLLECTION if article.source_type == "seed_sop" else FAQ_COLLECTION


async def _create_version(
    session,
    article: KnowledgeArticle,
    *,
    created_by: str,
    change_summary: str,
) -> KnowledgeArticleVersion:
    existing = await session.scalar(
        select(KnowledgeArticleVersion).where(
            KnowledgeArticleVersion.article_id == article.id,
            KnowledgeArticleVersion.content_hash == article.content_hash,
        )
    )
    if existing:
        return existing

    max_version = await session.scalar(
        select(func.max(KnowledgeArticleVersion.version_number)).where(
            KnowledgeArticleVersion.article_id == article.id
        )
    ) or 0
    version_number = max_version + 1
    version = KnowledgeArticleVersion(
        article_id=article.id,
        version_number=version_number,
        title=article.title,
        content=article.content,
        content_hash=article.content_hash,
        change_summary=change_summary,
        status=article.status,
        created_by=created_by,
    )
    session.add(version)
    article.current_version = version_number
    await session.flush()
    return version


async def create_knowledge_article(
    title: str,
    content: str,
    category: str | None = None,
    tags: list | None = None,
    source_ticket_id: str | None = None,
    source_conversation_id: uuid.UUID | None = None,
    status: str = "draft",
    meta_info: dict | None = None,
    *,
    canonical_key: str | None = None,
    source_type: str = "extracted",
    owner: str = "system",
) -> KnowledgeArticle:
    """Create or update a canonical knowledge asset with hash-based deduplication."""
    normalized_title = title.strip()[:500]
    normalized_content = content.strip()
    digest = content_hash(normalized_title, normalized_content)
    key = canonical_key or _canonical_key(
        title=normalized_title,
        content=normalized_content,
        source_type=source_type,
        source_ticket_id=source_ticket_id,
        source_conversation_id=source_conversation_id,
    )

    async with async_session_factory() as session:
        article = await session.scalar(
            select(KnowledgeArticle).where(KnowledgeArticle.canonical_key == key)
        )
        if article is None and status != "gap":
            article = await session.scalar(
                select(KnowledgeArticle).where(
                    KnowledgeArticle.content_hash == digest,
                    KnowledgeArticle.status != "rejected",
                )
            )

        if article is None:
            article = KnowledgeArticle(
                title=normalized_title,
                content=normalized_content,
                category=category or "other",
                tags=tags or [],
                source_ticket_id=source_ticket_id,
                source_conversation_id=source_conversation_id,
                status=status,
                meta_info=meta_info or {},
                canonical_key=key,
                content_hash=digest,
                source_type=source_type,
                current_version=1,
                owner=owner,
            )
            session.add(article)
            await session.flush()
            await _create_version(
                session,
                article,
                created_by=owner,
                change_summary="Initial version",
            )
        else:
            changed = article.content_hash != digest
            article.title = normalized_title
            article.content = normalized_content
            article.content_hash = digest
            article.category = category or article.category or "other"
            article.tags = tags or article.tags or []
            article.meta_info = {**(article.meta_info or {}), **(meta_info or {})}
            article.source_type = source_type or article.source_type
            article.owner = owner or article.owner
            if changed:
                article.status = status
                await _create_version(
                    session,
                    article,
                    created_by=owner,
                    change_summary="Content updated",
                )

        article.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(article)
        return article


async def get_article(article_id: uuid.UUID) -> KnowledgeArticle | None:
    async with async_session_factory() as session:
        return await session.scalar(
            select(KnowledgeArticle).where(KnowledgeArticle.id == article_id)
        )


async def list_articles(
    status: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[KnowledgeArticle], int]:
    async with async_session_factory() as session:
        stmt = select(KnowledgeArticle)
        count_stmt = select(func.count(KnowledgeArticle.id))
        if status:
            stmt = stmt.where(KnowledgeArticle.status == status)
            count_stmt = count_stmt.where(KnowledgeArticle.status == status)
        if category:
            stmt = stmt.where(KnowledgeArticle.category == category)
            count_stmt = count_stmt.where(KnowledgeArticle.category == category)
        total = await session.scalar(count_stmt) or 0
        stmt = stmt.order_by(KnowledgeArticle.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await session.scalars(stmt)).all())
        return rows, total


async def list_versions(article_id: uuid.UUID) -> list[KnowledgeArticleVersion]:
    async with async_session_factory() as session:
        rows = await session.scalars(
            select(KnowledgeArticleVersion)
            .where(KnowledgeArticleVersion.article_id == article_id)
            .order_by(KnowledgeArticleVersion.version_number.desc())
        )
        return list(rows.all())


async def publish_articles(article_ids: list[uuid.UUID]) -> list[KnowledgeArticle]:
    """Publish assets in batches; PostgreSQL remains the source of truth."""
    if not article_ids:
        return []
    async with async_session_factory() as session:
        articles = list((await session.scalars(
            select(KnowledgeArticle).where(KnowledgeArticle.id.in_(article_ids))
        )).all())
        documents_by_collection: dict[str, list[dict]] = {FAQ_COLLECTION: [], SOP_COLLECTION: []}
        chunk_lookup: dict[str, KnowledgeChunk] = {}
        now = datetime.now(timezone.utc)

        for article in articles:
            version = await _create_version(
                session,
                article,
                created_by=article.owner,
                change_summary="Published snapshot",
            )
            existing_chunks = list((await session.scalars(
                select(KnowledgeChunk).where(KnowledgeChunk.version_id == version.id)
            )).all())
            if not existing_chunks:
                for index, chunk_text in enumerate(_split_content(article.content)):
                    chunk = KnowledgeChunk(
                        version_id=version.id,
                        article_id=article.id,
                        chunk_index=index,
                        content=chunk_text,
                        content_hash=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                        token_count=max(1, len(chunk_text) // 2),
                        meta_info={"category": article.category, "tags": article.tags},
                    )
                    session.add(chunk)
                    await session.flush()
                    existing_chunks.append(chunk)

            collection = _collection_for(article)
            for chunk in existing_chunks:
                point_id = str(chunk.id)
                chunk_lookup[point_id] = chunk
                documents_by_collection[collection].append({
                    "id": point_id,
                    "title": article.title,
                    "content": chunk.content,
                    "category": article.category or "",
                    "tags": article.tags or [],
                    "article_id": str(article.id),
                    "version_id": str(version.id),
                    "chunk_id": point_id,
                    "source_type": article.source_type,
                })

            article.status = "approved"
            article.published_at = now
            article.retired_at = None
            version.status = "published"
            version.approved_by = "system" if article.owner == "system" else article.owner
            version.published_at = now

        for collection, documents in documents_by_collection.items():
            if documents:
                upsert_documents(collection, documents)
                for document in documents:
                    chunk_lookup[document["id"]].vector_point_id = document["id"]

        await session.commit()
        for article in articles:
            await session.refresh(article)
        return articles


async def approve_article(article_id: uuid.UUID) -> KnowledgeArticle:
    published = await publish_articles([article_id])
    if not published:
        raise ValueError(f"Knowledge article {article_id} not found")
    return published[0]


async def auto_approve_article(article_id: uuid.UUID) -> KnowledgeArticle:
    return await approve_article(article_id)


async def reject_article(article_id: uuid.UUID, reason: str = "") -> KnowledgeArticle:
    async with async_session_factory() as session:
        article = await session.get(KnowledgeArticle, article_id)
        if not article:
            raise ValueError(f"Knowledge article {article_id} not found")
        article.status = "rejected"
        article.updated_at = datetime.now(timezone.utc)
        article.meta_info = {**(article.meta_info or {}), "rejection_reason": reason}
        await session.commit()
        await session.refresh(article)
        return article


async def delete_article(article_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        article = await session.get(KnowledgeArticle, article_id)
        if not article:
            raise ValueError(f"Knowledge article {article_id} not found")
        point_ids = list((await session.scalars(
            select(KnowledgeChunk.vector_point_id).where(
                KnowledgeChunk.article_id == article_id,
                KnowledgeChunk.vector_point_id.is_not(None),
            )
        )).all())
        if point_ids:
            try:
                delete_documents(_collection_for(article), point_ids)
            except Exception as exc:
                logger.warning("Vector cleanup failed for %s: %s", article_id, exc)
        await session.delete(article)
        await session.commit()


async def track_knowledge_usage(source_ids: list[str], was_helpful: bool | None = None) -> int:
    """Track retrieval usage. Effectiveness is updated only from explicit feedback."""
    updated_articles: set[uuid.UUID] = set()
    async with async_session_factory() as session:
        for source_id in source_ids:
            try:
                source_uuid = uuid.UUID(source_id)
            except (ValueError, TypeError):
                continue
            article = await session.get(KnowledgeArticle, source_uuid)
            if article is None:
                chunk = await session.get(KnowledgeChunk, source_uuid)
                if chunk:
                    article = await session.get(KnowledgeArticle, chunk.article_id)
            if article and article.id not in updated_articles:
                article.usage_count = (article.usage_count or 0) + 1
                updated_articles.add(article.id)
        await session.commit()
    return len(updated_articles)


def _normalize_gap_query(query: str) -> str:
    value = query.strip()
    serialized = re.match(r"^content=(['\"])(.*?)\1\s+additional_kwargs=", value, re.DOTALL)
    if serialized:
        value = serialized.group(2)
    return re.sub(r"\s+", " ", value).strip()[:500]


async def create_gap_record(
    query: str,
    intent_label: str = "",
    conversation_id: uuid.UUID | None = None,
    top_retrieval_score: float = 0.0,
) -> KnowledgeArticle | None:
    normalized = _normalize_gap_query(query)
    if not normalized:
        return None
    key = f"gap:{hashlib.sha256(normalized.lower().encode('utf-8')).hexdigest()}"
    async with async_session_factory() as session:
        existing = await session.scalar(
            select(KnowledgeArticle).where(KnowledgeArticle.canonical_key == key)
        )
        if existing:
            return None
    return await create_knowledge_article(
        title=normalized,
        content="",
        category=intent_label or "other",
        tags=["knowledge_gap"],
        source_conversation_id=conversation_id,
        status="gap",
        meta_info={"top_retrieval_score": top_retrieval_score, "intent": intent_label},
        canonical_key=key,
        source_type="gap",
        owner="system",
    )


async def list_gaps(page: int = 1, page_size: int = 20) -> tuple[list[KnowledgeArticle], int]:
    return await _list_by_status("gap", page, page_size)


async def _list_by_status(status: str, page: int, page_size: int) -> tuple[list[KnowledgeArticle], int]:
    async with async_session_factory() as session:
        total = await session.scalar(
            select(func.count(KnowledgeArticle.id)).where(KnowledgeArticle.status == status)
        ) or 0
        rows = await session.scalars(
            select(KnowledgeArticle)
            .where(KnowledgeArticle.status == status)
            .order_by(KnowledgeArticle.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows.all()), total


async def fill_gap(
    gap_id: uuid.UUID,
    content: str,
    category: str | None = None,
    tags: list | None = None,
) -> KnowledgeArticle:
    async with async_session_factory() as session:
        article = await session.scalar(
            select(KnowledgeArticle).where(
                KnowledgeArticle.id == gap_id,
                KnowledgeArticle.status == "gap",
            )
        )
        if not article:
            raise ValueError(f"Gap record {gap_id} not found or not in 'gap' status")
        article.content = content.strip()
        article.content_hash = content_hash(article.title, article.content)
        article.category = category or article.category
        article.tags = [tag for tag in (tags or article.tags or []) if tag != "knowledge_gap"]
        article.source_type = "human_filled_gap"
        article.status = "draft"
        article.updated_at = datetime.now(timezone.utc)
        await _create_version(
            session,
            article,
            created_by="operator",
            change_summary="Filled knowledge gap",
        )
        await session.commit()
    return await approve_article(gap_id)


async def record_retrieval_event(
    *,
    conversation_id: str | None,
    query: str,
    rewritten_query: str | None,
    intent: str | None,
    results: list[dict],
    latency_ms: int,
    answered: bool,
) -> RetrievalEvent:
    article_ids = list(dict.fromkeys(
        str(result.get("article_id")) for result in results if result.get("article_id")
    ))
    async with async_session_factory() as session:
        event = RetrievalEvent(
            conversation_id=uuid.UUID(conversation_id) if conversation_id else None,
            query=query,
            rewritten_query=rewritten_query,
            intent=intent,
            result_ids=[str(result.get("id")) for result in results],
            result_scores=[float(result.get("score", 0)) for result in results],
            selected_article_ids=article_ids,
            latency_ms=latency_ms,
            answered=answered,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event


async def create_feedback(
    *,
    retrieval_event_id: uuid.UUID | None,
    conversation_id: uuid.UUID | None,
    article_id: uuid.UUID | None,
    feedback_type: str,
    score: float | None,
    comment: str | None,
    source: str,
) -> KnowledgeFeedback:
    async with async_session_factory() as session:
        # A chat message only needs to carry its retrieval event. Resolve the
        # primary cited article here so feedback still improves asset quality.
        if article_id is None and retrieval_event_id is not None:
            event = await session.get(RetrievalEvent, retrieval_event_id)
            if event and event.selected_article_ids:
                try:
                    article_id = uuid.UUID(event.selected_article_ids[0])
                except (TypeError, ValueError):
                    article_id = None

        effective_score = score
        if effective_score is None:
            effective_score = 1.0 if feedback_type in ("helpful", "resolved") else 0.0

        feedback = KnowledgeFeedback(
            retrieval_event_id=retrieval_event_id,
            conversation_id=conversation_id,
            article_id=article_id,
            feedback_type=feedback_type,
            score=effective_score,
            comment=comment,
            source=source,
        )
        session.add(feedback)
        await session.flush()
        if article_id:
            article = await session.get(KnowledgeArticle, article_id)
            if article:
                average_score = await session.scalar(
                    select(func.avg(KnowledgeFeedback.score)).where(
                        KnowledgeFeedback.article_id == article_id
                    )
                )
                article.effectiveness_score = round(float(average_score or 0), 4)
                article.quality_score = round(
                    0.6 * article.effectiveness_score
                    + 0.25 * min(article.usage_count / 20, 1)
                    + 0.15 * (1 if article.status == "approved" else 0),
                    4,
                )
        await session.commit()
        await session.refresh(feedback)
        return feedback
