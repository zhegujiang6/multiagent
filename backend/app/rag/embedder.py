"""Embedding generator — supports local SentenceTransformer and remote OpenAI-compatible API."""

from openai import OpenAI
from app.core.config import settings

_embedder: object | None = None
_api_client: OpenAI | None = None
_use_api: bool | None = None


def _should_use_api() -> bool:
    """Determine whether to use the remote API or local model."""
    global _use_api
    if _use_api is None:
        _use_api = bool(settings.embedding_api_key and settings.embedding_api_base)
    return _use_api


def get_embedder():
    """Lazily load the local embedding model."""
    global _embedder
    if not _should_use_api() and _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Local embeddings require requirements-local-embeddings.txt; "
                "configure EMBEDDING_API_KEY/EMBEDDING_API_BASE or install it"
            ) from exc
        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def _get_api_client() -> OpenAI:
    global _api_client
    if _api_client is None:
        _api_client = OpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_api_base,
        )
    return _api_client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    if _should_use_api():
        client = _get_api_client()
        resp = client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        return [d.embedding for d in resp.data]

    model = get_embedder()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def embed_text(text: str) -> list[float]:
    """Generate embedding for a single text."""
    return embed_texts([text])[0]


def get_embedding_dim() -> int:
    return settings.embedding_dim
