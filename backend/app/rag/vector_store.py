"""Qdrant vector store wrapper for RAG."""

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.rag.embedder import embed_texts, get_embedding_dim

_client: QdrantClient | None = None

# Collection names
FAQ_COLLECTION = "faq_articles"
PRODUCT_COLLECTION = "product_docs"
SOP_COLLECTION = "sop_documents"
TICKET_RESOLUTION_COLLECTION = "ticket_resolutions"

ALL_COLLECTIONS = [FAQ_COLLECTION, PRODUCT_COLLECTION, SOP_COLLECTION, TICKET_RESOLUTION_COLLECTION]


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=10.0,  # Fail fast if Qdrant is unreachable
        )
    return _client


def ensure_collections():
    """Create all required collections if they don't exist."""
    client = get_client()
    dim = get_embedding_dim()

    for name in ALL_COLLECTIONS:
        try:
            client.get_collection(name)
        except UnexpectedResponse:
            client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=dim,
                    distance=models.Distance.COSINE,
                ),
            )


def recreate_collection(collection_name: str) -> None:
    """Rebuild one derived vector index from PostgreSQL knowledge assets."""
    client = get_client()
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=get_embedding_dim(),
            distance=models.Distance.COSINE,
        ),
    )


def upsert_documents(
    collection_name: str,
    documents: list[dict],
    batch_size: int = 8,
):
    """Insert/update documents with embeddings into a Qdrant collection.

    Each document dict must have:
        - id: str (unique)
        - title: str
        - content: str
        - category: str (optional)
        - tags: list[str] (optional)
    """
    client = get_client()
    ensure_collections()

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        texts = [f"{doc['title']}\n{doc['content']}" for doc in batch]
        embeddings = embed_texts(texts)

        points = []
        for j, doc in enumerate(batch):
            point_id = doc.get("id", str(hash(doc["title"] + doc["content"])))
            if isinstance(point_id, str):
                from uuid import UUID, uuid5, NAMESPACE_DNS
                try:
                    point_id = str(UUID(point_id))
                except ValueError:
                    point_id = str(uuid5(NAMESPACE_DNS, point_id))

            payload = {
                "title": doc["title"],
                "content": doc["content"],
                "category": doc.get("category", ""),
                "tags": doc.get("tags", []),
                "article_id": doc.get("article_id"),
                "version_id": doc.get("version_id"),
                "chunk_id": doc.get("chunk_id"),
                "source_type": doc.get("source_type", "manual"),
            }
            points.append(models.PointStruct(
                id=point_id,
                vector=embeddings[j],
                payload=payload,
            ))

        client.upsert(collection_name=collection_name, points=points)


def search(
    collection_name: str,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.3,
) -> list[dict]:
    """Semantic search in a Qdrant collection."""
    client = get_client()
    from app.rag.embedder import embed_text
    query_vector = embed_text(query)

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
    )

    return [
        {
            "id": str(r.id),
            "title": r.payload.get("title", ""),
            "content": r.payload.get("content", ""),
            "category": r.payload.get("category", ""),
            "tags": r.payload.get("tags", []),
            "article_id": r.payload.get("article_id"),
            "version_id": r.payload.get("version_id"),
            "chunk_id": r.payload.get("chunk_id"),
            "source_type": r.payload.get("source_type", ""),
            "score": round(r.score, 4),
        }
        for r in results.points
    ]


def search_multi_collection(
    query: str,
    collections: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Search across multiple collections and merge results."""
    if collections is None:
        collections = [FAQ_COLLECTION]

    all_results = []
    for col in collections:
        results = search(col, query, top_k=top_k)
        for r in results:
            r["source_collection"] = col
        all_results.extend(results)

    # Deduplicate by title and sort by score
    seen = set()
    deduped = []
    for r in sorted(all_results, key=lambda x: x["score"], reverse=True):
        if r["title"] not in seen:
            seen.add(r["title"])
            deduped.append(r)

    return deduped[:top_k]


def delete_document(collection_name: str, doc_id: str) -> None:
    """Remove a document from a Qdrant collection by its point ID."""
    client = get_client()
    from qdrant_client.http import models as qmodels
    client.delete(
        collection_name=collection_name,
        points_selector=qmodels.PointIdsList(
            points=[doc_id],
        ),
    )


def delete_documents(collection_name: str, doc_ids: list[str]) -> None:
    """Remove multiple vector points from one collection."""
    if not doc_ids:
        return
    client = get_client()
    client.delete(
        collection_name=collection_name,
        points_selector=models.PointIdsList(points=doc_ids),
    )
