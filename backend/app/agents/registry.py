"""Agent registry — discovery and factory for all agents."""

from openai import AsyncOpenAI

from app.agents.base import BaseAgent
from app.agents.intent_classifier import IntentClassifierAgent
from app.agents.sentiment_analyzer import SentimentAnalyzerAgent
from app.agents.faq_agent import FAQAgent
from app.agents.profile_enricher import ProfileEnricherAgent
from app.agents.ticket_agent import TicketAgent


class AgentRegistry:
    """Central registry for creating and looking up agents."""

    def __init__(self, llm_client: AsyncOpenAI):
        self.llm = llm_client
        self._agents: dict[str, BaseAgent] = {}

    def initialize(self):
        """Create all agent instances."""
        self._agents = {
            "intent_classifier": IntentClassifierAgent(self.llm),
            "sentiment_analyzer": SentimentAnalyzerAgent(self.llm),
            "faq_agent": FAQAgent(self.llm),
            "profile_enricher": ProfileEnricherAgent(self.llm),
            "ticket_agent": TicketAgent(self.llm),
        }
        return self

    def get(self, name: str) -> BaseAgent:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found in registry")
        return self._agents[name]

    @property
    def all_agents(self) -> dict[str, BaseAgent]:
        return self._agents
