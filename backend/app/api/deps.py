"""FastAPI dependency injection."""

from fastapi import Header, HTTPException, status


async def verify_api_key(x_api_key: str = Header(None)) -> str:
    """Simple API key verification for MVP."""
    # MVP: accept demo tokens or skip if not provided
    if x_api_key in (None, "demo-admin-token", "demo-agent-token"):
        return x_api_key or "anonymous"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )
