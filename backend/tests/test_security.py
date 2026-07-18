"""Security utility tests."""

from app.core.security import mask_pii, verify_token


def test_mask_pii_hides_supported_values() -> None:
    text = "电话 13800138000，邮箱 user@example.com，银行卡 6222021234567890123"
    masked = mask_pii(text)

    assert "13800138000" not in masked
    assert "user@example.com" not in masked
    assert "6222021234567890123" not in masked
    assert "[手机号已隐藏]" in masked
    assert "[邮箱已隐藏]" in masked
    assert "[银行卡号已隐藏]" in masked


def test_verify_token_rejects_unknown_token() -> None:
    assert verify_token("demo-agent-token") is True
    assert verify_token("not-a-valid-token") is False
