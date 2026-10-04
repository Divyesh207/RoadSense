"""
The rate limiter itself. Other tests start with an empty rate-limit window (see the
`isolated_rate_limiter` fixture in conftest.py); these tests fill a window on purpose.
"""

import pytest
from httpx import AsyncClient

from app.core.config import Settings, settings
from app.core.middleware import rate_limit_store
from app.core.security import create_access_token
from tests.conftest import ADMIN_USER_ID, ORG_1_ID

LOGIN = "/api/v1/auth/login"
BAD_CREDENTIALS = {"email": "nobody@example.com", "password": "wrong-password"}


def _headers() -> dict[str, str]:
    token, _ = create_access_token(ADMIN_USER_ID)
    return {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}


def test_default_limits_are_unchanged():
    """Production defaults: 30 login attempts and 300 other requests per minute, limiter on."""
    defaults = Settings.model_fields
    assert defaults["RATE_LIMIT_ENABLED"].default is True
    assert defaults["RATE_LIMIT_AUTH_PER_MINUTE"].default == 30
    assert defaults["RATE_LIMIT_DEFAULT_PER_MINUTE"].default == 300


def test_limiter_is_enabled_in_the_test_suite():
    """The suite isolates the limiter's state; it does not switch the limiter off."""
    assert settings.RATE_LIMIT_ENABLED is True


@pytest.mark.asyncio
async def test_requests_below_the_limit_succeed(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MINUTE", 5)
    for expected_remaining in (4, 3, 2, 1, 0):
        resp = await async_client.get("/api/v1/roads", headers=_headers())
        assert resp.status_code == 200
        assert resp.headers["X-RateLimit-Limit"] == "5"
        assert resp.headers["X-RateLimit-Remaining"] == str(expected_remaining)


@pytest.mark.asyncio
async def test_exceeding_the_limit_returns_429_in_the_standard_envelope(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MINUTE", 3)
    for _ in range(3):
        assert (await async_client.get("/api/v1/roads", headers=_headers())).status_code == 200

    blocked = await async_client.get("/api/v1/roads", headers=_headers())
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert body["error"]["message"] == "Rate limit exceeded. Maximum 3 requests per minute allowed."
    assert body["meta"]["request_id"]
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.headers["X-RateLimit-Limit"] == "3"
    assert blocked.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in blocked.headers


@pytest.mark.asyncio
async def test_login_uses_its_own_stricter_limit(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 2)
    for _ in range(2):
        assert (await async_client.post(LOGIN, json=BAD_CREDENTIALS)).status_code == 401
    blocked = await async_client.post(LOGIN, json=BAD_CREDENTIALS)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["message"] == "Rate limit exceeded. Maximum 2 requests per minute allowed."
    # The login limit does not consume the general allowance.
    assert (await async_client.get("/api/v1/roads", headers=_headers())).status_code == 200


@pytest.mark.asyncio
async def test_clients_are_limited_separately(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 1)
    first = {"X-Forwarded-For": "203.0.113.10"}
    second = {"X-Forwarded-For": "203.0.113.20"}
    assert (await async_client.post(LOGIN, json=BAD_CREDENTIALS, headers=first)).status_code == 401
    assert (await async_client.post(LOGIN, json=BAD_CREDENTIALS, headers=first)).status_code == 429
    assert (await async_client.post(LOGIN, json=BAD_CREDENTIALS, headers=second)).status_code == 401


@pytest.mark.asyncio
async def test_no_request_header_bypasses_the_limiter(async_client: AsyncClient, monkeypatch):
    """A client must not be able to opt out of rate limiting."""
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 1)
    bypass = {"X-Bypass-Rate-Limit": "test-bypass"}
    assert (await async_client.post(LOGIN, json=BAD_CREDENTIALS, headers=bypass)).status_code == 401
    assert (await async_client.post(LOGIN, json=BAD_CREDENTIALS, headers=bypass)).status_code == 429


@pytest.mark.asyncio
async def test_each_test_starts_with_an_empty_window(async_client: AsyncClient):
    """Guards the isolation fixture: nothing from earlier tests is still counted."""
    assert rate_limit_store.request_history == {}
    resp = await async_client.post(LOGIN, json=BAD_CREDENTIALS)
    assert resp.status_code == 401
    assert resp.headers["X-RateLimit-Remaining"] == str(settings.RATE_LIMIT_AUTH_PER_MINUTE - 1)


@pytest.mark.asyncio
async def test_disabled_limiter_lets_everything_through(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 1)
    for _ in range(3):
        assert (await async_client.post(LOGIN, json=BAD_CREDENTIALS)).status_code == 401
