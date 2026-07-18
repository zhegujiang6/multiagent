"""Application entry-point smoke tests."""

import asyncio

from app.main import app, root


def test_required_routes_are_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert {
        "/",
        "/api/v1/health",
        "/api/v1/conversations",
        "/api/v1/tickets",
        "/api/v1/knowledge/articles",
    } <= paths


def test_root_response() -> None:
    response = asyncio.run(root())
    assert response["status"] == "running"
    assert response["version"] == "0.1.0"
