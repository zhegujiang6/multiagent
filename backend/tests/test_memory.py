"""Pure unit tests for the durable memory policy."""

from app.services.memory_service import derive_satisfaction, format_memory_for_prompt


def test_explicit_feedback_overrides_inferred_sentiment() -> None:
    assert derive_satisfaction({"label": "angry"}, explicit_feedback="helpful") == "satisfied"
    assert derive_satisfaction({"label": "satisfied"}, explicit_feedback="unhelpful") == "dissatisfied"


def test_prompt_memory_is_bounded_and_task_oriented() -> None:
    prompt = format_memory_for_prompt(
        {
            "summary": "用户目标：查询退款进度\n已完成：已确认订单\n待处理：等待财务审核",
        },
        {
            "conversation_count": 3,
            "satisfaction": "dissatisfied",
            "open_tasks": ["向用户同步退款审核进度"],
            "preferences": ["优先中文回复"],
        },
    )

    assert "用户目标：查询退款进度" in prompt
    assert "历史会话数：3" in prompt
    assert "跨会话待办：向用户同步退款审核进度" in prompt
    assert "服务偏好：优先中文回复" in prompt
