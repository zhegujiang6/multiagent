"""Multi-path RAG retriever with query rewriting and result fusion."""

import asyncio
import logging

from app.core.llm import get_async_llm_client, FAST_MODEL
from app.rag.vector_store import (
    search_multi_collection,
    FAQ_COLLECTION,
    SOP_COLLECTION,
    TICKET_RESOLUTION_COLLECTION,
)
from app.core.security import mask_pii
from app.agents.base import _extract_response_content


async def rewrite_query(query: str) -> str:
    """Use LLM to rewrite user query for better retrieval.

    Converts informal/vague queries into precise search queries.
    """
    import asyncio as _asyncio
    client = get_async_llm_client()
    try:
        resp = await _asyncio.wait_for(
            client.chat.completions.create(
                model=FAST_MODEL,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": "将用户的不规范问题改写为一个简洁的检索查询。只输出改写后的查询，不要解释。"},
                    {"role": "user", "content": query},
                ],
            ),
            timeout=10.0,
        )
        rewritten = _extract_response_content(resp) or ""
        rewritten = rewritten.strip()
        return rewritten if rewritten else query
    except Exception:
        return query


async def multi_path_retrieve(
    query: str,
    top_k: int = 5,
    search_sop: bool = False,
    search_resolutions: bool = False,
) -> list[dict]:
    """Multi-path retrieval with query rewriting and result fusion.

    Args:
        query: User query text
        top_k: Number of results to return
        search_sop: Whether to search SOP documents
        search_resolutions: Whether to search historical ticket resolutions

    Returns:
        List of knowledge results sorted by relevance
    """
    # Path 1: Query rewriting for better recall
    rewritten = await rewrite_query(query)

    # Path 2: Multi-collection search
    collections = [FAQ_COLLECTION]
    if search_sop:
        collections.append(SOP_COLLECTION)
    if search_resolutions:
        collections.append(TICKET_RESOLUTION_COLLECTION)

    # Search with original and rewritten queries in parallel (with timeouts)
    try:
        original_results, rewritten_results = await asyncio.gather(
            asyncio.wait_for(
                asyncio.to_thread(search_multi_collection, query, collections, top_k),
                timeout=8.0,
            ),
            asyncio.wait_for(
                asyncio.to_thread(search_multi_collection, rewritten, collections, top_k),
                timeout=8.0,
            ),
        )
    except asyncio.TimeoutError:
        logging.getLogger("customer_service.rag").warning("Qdrant search timed out — returning empty results")
        return []
    except Exception:
        logging.getLogger("customer_service.rag").warning("Qdrant search failed — returning empty results")
        return []

    # Fusion: deduplicate by title, take best score
    seen: set[str] = set()
    fused: list[dict] = []
    for r in sorted(original_results + rewritten_results, key=lambda x: x["score"], reverse=True):
        key = r["title"]
        if key not in seen:
            seen.add(key)
            fused.append(r)

    # Mask PII in retrieved content before returning
    for r in fused:
        r["content"] = mask_pii(r["content"])

    return fused[:top_k]


def build_knowledge_context(results: list[dict]) -> str:
    """Build a context string from retrieved knowledge for LLM prompt injection."""
    if not results:
        return "（未找到相关知识库条目）"

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[知识{i}] 标题: {r['title']}\n"
            f"分类: {r.get('category', 'N/A')} | 相关度: {r['score']}\n"
            f"内容: {r['content']}\n"
        )
    return "\n".join(parts)
