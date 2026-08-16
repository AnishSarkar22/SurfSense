from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.context import AuthContext
from app.db import Report, get_async_session
from app.routes import reports_routes
from app.users import get_auth_context


@pytest.mark.asyncio
async def test_report_content_uses_full_auth_context(monkeypatch):
    auth = AuthContext.session(SimpleNamespace(id="user-1"))
    report = Report(
        id=1,
        title="Test report",
        content="Report body",
        content_type="markdown",
        report_metadata=None,
        report_group_id=None,
        workspace_id=7,
    )
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(first=lambda: report)
    )

    async def check_access(_session, received_auth, workspace_id):
        assert received_auth is auth
        assert workspace_id == 7

    monkeypatch.setattr(reports_routes, "check_workspace_access", check_access)

    app = FastAPI()
    app.include_router(reports_routes.router, prefix="/api/v1")
    app.dependency_overrides[get_auth_context] = lambda: auth

    async def get_session():
        yield session

    app.dependency_overrides[get_async_session] = get_session

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/reports/1/content")

    assert response.status_code == 200
    assert response.json()["content"] == "Report body"
