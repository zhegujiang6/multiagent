"""Security utilities: PII masking, simple API key auth."""

import re
from functools import lru_cache

# ── PII patterns ──
PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b1[3-9]\d{9}\b", "[手机号已隐藏]"),
    (r"\b\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b", "[身份证已隐藏]"),
    (r"\b\d{16,19}\b", "[银行卡号已隐藏]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[邮箱已隐藏]"),
    (
        r"\b(?:(?:https?|ftp)://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?\b",
        "[链接已移除]",
    ),
]


def mask_pii(text: str) -> str:
    """Replace personally identifiable information with placeholders."""
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


# ── Simple API Key validation (MVP) ──
VALID_TOKENS: set[str] = {"demo-admin-token", "demo-agent-token"}


def verify_token(token: str) -> bool:
    return token in VALID_TOKENS
