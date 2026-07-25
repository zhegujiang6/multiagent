from app.agents.intent_classifier import classify_intent_with_rules


def test_refund_fallback_extracts_order_id():
    result = classify_intent_with_rules(
        "我要申请订单退款，订单号 ORD-20260725-1001，请创建工单。"
    )

    assert result["label"] == "refund"
    assert result["confidence"] >= 0.8
    assert result["entities"] == [
        {"name": "order_id", "value": "ord-20260725-1001"}
    ]


def test_fallback_prefers_refund_over_generic_order_inquiry():
    result = classify_intent_with_rules("订单 ORD-1001 一直没有退款到账")

    assert result["label"] == "refund"


def test_unknown_question_remains_faq():
    result = classify_intent_with_rules("你们周末几点上班？")

    assert result["label"] == "faq"
