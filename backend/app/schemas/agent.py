"""Agent State — the shared state flowing through the LangGraph StateGraph.

This is the central contract that all agents read from and write to.
Uses LangGraph's TypedDict + Annotated pattern for proper state management.
"""

from typing import Annotated, Any, TypedDict
from langgraph.graph.message import add_messages


class IntentResult(TypedDict, total=False):
    label: str
    confidence: float
    entities: list[dict[str, str]]


class SentimentResult(TypedDict, total=False):
    label: str
    score: float
    trend: str
    triggers: list[str]


class ProfileResult(TypedDict, total=False):
    tier: str
    history_count: int
    tags: list[str]
    name: str
    email: str


class TicketDraft(TypedDict, total=False):
    title: str
    category: str
    priority: str
    description: str


class KnowledgeResult(TypedDict, total=False):
    title: str
    content: str
    score: float
    source: str


class AgentState(TypedDict, total=False):
    """Shared state flowing through the LangGraph StateGraph.

    All fields are optional (`total=False`) to allow incremental population
    by different agent nodes in the graph.
    """

    messages: Annotated[list[dict[str, Any]], add_messages]
    conversation_id: str
    customer_id: str
    request_id: str
    session_memory: dict[str, Any]
    user_memory: dict[str, Any]
    memory_context: str

    # Populated by parallel preprocessing
    intent: IntentResult | None
    sentiment: SentimentResult | None

    # Populated by profile enricher
    profile: ProfileResult | None

    # Populated by FAQ agent (RAG)
    retrieved_knowledge: list[KnowledgeResult] | None
    retrieval_event_id: str | None

    # Populated by leaf nodes
    response: str | None
    should_escalate: bool
    should_create_ticket: bool
    ticket_draft: TicketDraft | None
    ticket_id: str | None
    ticket: dict[str, Any] | None

    # Audit trail
    agent_decisions: list[dict[str, Any]]

    # Error handling
    error: str | None
