"""Profile Enricher Agent — enhances user context from database/CMS."""

import logging
from typing import Any

from sqlalchemy import select
from openai import AsyncOpenAI

from app.agents.base import BaseAgent
from app.schemas.agent import AgentState
from app.core.database import async_session_factory
from app.models.user import User

logger = logging.getLogger("customer_service.agents.profile")

# Mock tier-based handling notes
TIER_NOTES = {
    "vip": "VIP用户，需优先处理，授权额度翻倍，语气要更主动热情",
    "premium": "Premium用户，服务质量高于普通用户，关注其满意度",
    "standard": "普通用户，按标准流程服务",
}


class ProfileEnricherAgent(BaseAgent):
    def __init__(self, llm_client: AsyncOpenAI):
        super().__init__("profile_enricher", llm_client)

    async def execute(self, state: AgentState) -> dict[str, Any]:
        customer_id = state.get("customer_id", "")

        if not customer_id or customer_id == "anonymous":
            # Anonymous user — return default profile
            return {
                "profile": {
                    "tier": "standard",
                    "history_count": 0,
                    "tags": [],
                    "name": "访客",
                    "email": "",
                    "special_handling": "",
                    "suggested_tone": "友好专业",
                }
            }

        try:
            async with async_session_factory() as session:
                stmt = select(User).where(
                    (User.id == customer_id) | (User.external_id == customer_id)
                )
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user:
                    tier = user.tier or "standard"
                    profile = {
                        "tier": tier,
                        "history_count": 0,  # MVP: count from conversations table later
                        "tags": user.tags or [],
                        "name": user.name or "",
                        "email": user.email or "",
                        "special_handling": TIER_NOTES.get(tier, ""),
                        "suggested_tone": "热情主动" if tier == "vip" else "友好专业",
                    }
                else:
                    profile = {
                        "tier": "standard",
                        "history_count": 0,
                        "tags": [],
                        "name": "",
                        "email": "",
                        "special_handling": "",
                        "suggested_tone": "友好专业",
                    }
        except Exception as e:
            logger.warning(f"Profile enrichment failed: {e}")
            profile = {
                "tier": "standard",
                "history_count": 0,
                "tags": [],
                "name": "",
                "email": "",
                "special_handling": "",
                "suggested_tone": "友好专业",
            }

        return {
            "profile": profile,
            "agent_decisions": [{"agent": "profile_enricher", "decision": f"tier={profile['tier']}"}],
        }
