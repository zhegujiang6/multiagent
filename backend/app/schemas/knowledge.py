"""Knowledge management Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeArticleResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    category: str | None = None
    tags: list = []
    source_ticket_id: str | None = None
    source_conversation_id: uuid.UUID | None = None
    status: str = "draft"
    canonical_key: str = ""
    content_hash: str = ""
    source_type: str = "manual"
    current_version: int = 1
    owner: str = "system"
    quality_score: float = 0.0
    effectiveness_score: float = 0.0
    usage_count: int = 0
    published_at: datetime | None = None
    retired_at: datetime | None = None
    meta_info: dict = Field(default={}, serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeArticleListResponse(BaseModel):
    articles: list[KnowledgeArticleResponse]
    total: int
    page: int
    page_size: int


class ExtractKnowledgeResponse(BaseModel):
    conversation_id: str
    extracted_pairs: list[dict]
    saved_count: int = 0
    auto_approved_count: int = 0
    drafted_count: int = 0
    discarded_count: int = 0


class RejectArticleRequest(BaseModel):
    reason: str = ""


class FillGapRequest(BaseModel):
    content: str
    category: str | None = None
    tags: list | None = None


class CreateKnowledgeArticleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=20000)
    category: str = "other"
    tags: list[str] = []
    owner: str = "operator"


class KnowledgeVersionResponse(BaseModel):
    id: uuid.UUID
    article_id: uuid.UUID
    version_number: int
    title: str
    content: str
    content_hash: str
    change_summary: str | None = None
    status: str
    created_by: str
    approved_by: str | None = None
    created_at: datetime
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class KnowledgeFeedbackRequest(BaseModel):
    retrieval_event_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    article_id: uuid.UUID | None = None
    feedback_type: str = Field(..., pattern=r"^(helpful|unhelpful|followup|escalated|resolved)$")
    score: float | None = Field(None, ge=0, le=1)
    comment: str | None = Field(None, max_length=2000)
    source: str = "user"


class KnowledgeFeedbackResponse(BaseModel):
    id: uuid.UUID
    retrieval_event_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    article_id: uuid.UUID | None = None
    feedback_type: str
    score: float | None = None
    comment: str | None = None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GapStatsResponse(BaseModel):
    """Summary stats for the knowledge self-evolution dashboard."""
    total_gaps: int
    total_articles: int
    total_approved: int
    total_drafts: int
    total_rejected: int = 0
    total_versions: int = 0
    total_chunks: int = 0
    retrievals_24h: int = 0
    answered_retrievals_24h: int = 0
    feedback_count: int = 0
    helpful_rate: float = 0.0
    avg_effectiveness: float
