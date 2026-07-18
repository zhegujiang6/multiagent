"""Knowledge extraction service — uses LLM to extract Q&A pairs from conversations."""

import json
import logging

from app.core.llm import get_async_llm_client, DEFAULT_MODEL
from app.services.conversation_service import get_messages
from app.agents.base import _extract_response_content

logger = logging.getLogger("customer_service.services.knowledge_extraction")

EXTRACTION_SYSTEM_PROMPT = """你是一个客服知识提炼专家。分析以下对话，提取其中有价值的问答对，用于未来自动回答类似问题。

## 提取规则：
1. 只提取客服成功解决的问题（客户表示满意或问题已解决的对话片段）
2. 每个问答对需要：一个简洁的问题标题（15字以内）、完整的问题描述、准确的答案、合适的分类、相关标签
3. 如果某条知识是系统已有FAQ/SOP的直接应用，confidence给0.7-0.9
4. 如果某条知识是客服通过推理/组合多个来源得出的新方案，confidence给0.5-0.7
5. 如果对话中客服未能有效解决问题，提取无价值知识，返回空列表
6. 知识类别从以下选择：order, refund, account, product, payment, shipping, tech_support, membership, other

## 输出格式（严格JSON）：
{
  "pairs": [
    {
      "title": "简洁的问题标题（15字以内）",
      "question": "完整的问题描述",
      "answer": "标准化的解答",
      "category": "类别",
      "tags": ["标签1", "标签2"],
      "confidence": 0.85
    }
  ]
}
只输出JSON，不要任何其他文字。"""


async def extract_knowledge_from_conversation(
    conversation_id: str,
    max_pairs: int = 5,
) -> list[dict]:
    """Extract structured Q&A pairs from a resolved conversation.

    Args:
        conversation_id: UUID of the conversation to analyze.
        max_pairs: Maximum number of Q&A pairs to extract.

    Returns:
        List of dicts, each with: title, question, answer, category, tags, confidence.
        Returns empty list on failure or if no valuable knowledge found.
    """
    # 1. Fetch conversation messages
    try:
        messages = await get_messages(conversation_id, limit=100)
    except Exception as e:
        logger.error(f"Failed to fetch messages for conversation {conversation_id}: {e}")
        return []

    if len(messages) < 2:
        logger.info(f"Conversation {conversation_id} has too few messages to extract knowledge")
        return []

    # 2. Build conversation text
    parts = []
    for m in messages:
        role_label = "用户" if m.role == "customer" else ("客服" if m.role == "agent" else "系统")
        parts.append(f"[{role_label}]: {m.content}")

    conversation_text = "\n".join(parts)

    # 3. Call LLM
    client = get_async_llm_client()
    try:
        resp = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            max_tokens=2048,
            temperature=0.3,  # Low temperature for extraction tasks
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"请分析以下客服对话，提取有价值的知识问答对：\n\n{conversation_text}"},
            ],
        )
        raw = _extract_response_content(resp) or ""
    except Exception as e:
        logger.error(f"LLM call failed during knowledge extraction: {e}")
        return []

    # 4. Parse JSON
    try:
        cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(cleaned)
        pairs = result.get("pairs", [])
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse extraction result: {e}\nRaw: {raw[:500]}")
        return []

    # 5. Validate and limit
    valid_pairs = []
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        if not pair.get("title") or not pair.get("question") or not pair.get("answer"):
            continue
        valid_pairs.append({
            "title": pair["title"][:500],
            "question": pair["question"][:2000],
            "answer": pair["answer"][:2000],
            "category": pair.get("category", "other"),
            "tags": pair.get("tags", [])[:10],  # Max 10 tags
            "confidence": min(max(float(pair.get("confidence", 0.5)), 0.0), 1.0),
        })
        if len(valid_pairs) >= max_pairs:
            break

    if valid_pairs:
        logger.info(
            f"Extracted {len(valid_pairs)} knowledge pairs from conversation {conversation_id}"
        )

    return valid_pairs
