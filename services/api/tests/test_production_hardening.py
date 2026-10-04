import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.services.audit_service import AuditService
from tests.conftest import (
    ADMIN_USER_ID,
    AUTHORITY_USER_ID,
    INSPECTOR_USER_ID,
    ORG_1_ID,
    ORG_2_ID,
    OTHER_ORG_USER_ID,
)


@pytest.fixture
def admin_headers():
    token, _ = create_access_token(ADMIN_USER_ID)
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(ORG_1_ID),
    }


@pytest.fixture
def authority_headers():
    token, _ = create_access_token(AUTHORITY_USER_ID)
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(ORG_1_ID),
    }


@pytest.fixture
def inspector_headers():
    token, _ = create_access_token(INSPECTOR_USER_ID)
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(ORG_1_ID),
    }


@pytest.fixture
def other_org_headers():
    token, _ = create_access_token(OTHER_ORG_USER_ID)
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(ORG_2_ID),
    }


@pytest.mark.asyncio
async def test_security_headers_present_on_all_responses(async_client: AsyncClient):
    """
    Test that OWASP recommended security headers are present on API responses.
    """
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation" in headers.get("Permissions-Policy", "")
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "X-Request-ID" in headers
    assert "X-Process-Time-Ms" in headers


@pytest.mark.asyncio
async def test_request_payload_size_limit(async_client: AsyncClient):
    """
    Test that requests exceeding the maximum payload limit return 413 Payload Too Large.
    """
    oversized_length = settings.MAX_REQUEST_SIZE_BYTES + 1024
    response = await async_client.post(
        "/api/v1/roads",
        headers={"Content-Length": str(oversized_length)},
        content=b"test",
    )
    assert response.status_code == 413
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"


@pytest.mark.asyncio
async def test_rate_limiter_triggers_429(async_client: AsyncClient):
    """
    Test that rapid requests to rate-limited paths trigger HTTP 429 Too Many Requests.
    """
    # Temporarily set a very small auth limit
    original_auth_limit = settings.RATE_LIMIT_AUTH_PER_MINUTE
    settings.RATE_LIMIT_AUTH_PER_MINUTE = 3

    try:
        for _ in range(3):
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "wrong@example.com", "password": "wrongpassword"},
            )
            # Either 401 (invalid creds) or 429
            assert resp.status_code in [401, 429]

        # 4th request must be rate limited
        blocked_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpassword"},
        )
        assert blocked_resp.status_code == 429
        body = blocked_resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in blocked_resp.headers
        assert "X-RateLimit-Limit" in blocked_resp.headers
    finally:
        settings.RATE_LIMIT_AUTH_PER_MINUTE = original_auth_limit


@pytest.mark.asyncio
async def test_audit_service_and_api(
    async_client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict,
    inspector_headers: dict,
    other_org_headers: dict,
):
    """
    Test recording audit logs, querying them with RBAC, and ensuring tenant isolation.
    """
    target_id = uuid.uuid4()
    await AuditService.record_audit_event(
        db=db_session,
        action="DAMAGE_CONFIRMED",
        entity_type="damage_record",
        entity_id=target_id,
        actor_user_id=ADMIN_USER_ID,
        organization_id=ORG_1_ID,
        request_id="req-test-audit-1",
        before_data={"status": "PENDING_REVIEW"},
        after_data={"status": "CONFIRMED"},
        metadata={"notes": "Confirmed by senior engineer"},
        ip_address="127.0.0.1",
        user_agent="Pytest-TestClient",
    )
    await db_session.commit()

    # 1. Admin queries audit logs -> Success
    res = await async_client.get("/api/v1/audit-logs", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["meta"]["total_count"] >= 1
    found = any(item["action"] == "DAMAGE_CONFIRMED" for item in body["data"])
    assert found is True

    # 2. Filter by action
    res_filtered = await async_client.get("/api/v1/audit-logs?action=DAMAGE_CONFIRMED", headers=admin_headers)
    assert res_filtered.status_code == 200
    assert len(res_filtered.json()["data"]) >= 1

    # 3. Field Inspector lacks role -> 403 Forbidden
    res_insp = await async_client.get("/api/v1/audit-logs", headers=inspector_headers)
    assert res_insp.status_code == 403

    # 4. Cross-organization isolation check: other org user trying to access ORG_1 is denied
    cross_org_headers = dict(other_org_headers)
    cross_org_headers["X-Organization-ID"] = str(ORG_1_ID)
    res_cross = await async_client.get("/api/v1/audit-logs", headers=cross_org_headers)
    assert res_cross.status_code == 403
    assert res_cross.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

    # Also check that an admin in ORG_2 cannot see ORG_1 logs (strict tenant isolation)
    from app.models.identity import OrganizationMembership, Role, User
    admin_org2_id = uuid.uuid4()
    admin_role = (await db_session.execute(select(Role).where(Role.code == "ADMINISTRATOR"))).scalar_one()
    u2 = User(
        id=admin_org2_id,
        email="admin2@org2.com",
        password_hash="pw",
        full_name="Org 2 Admin",
        is_active=True,
    )
    m2 = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=ORG_2_ID,
        user_id=admin_org2_id,
        role_id=admin_role.id,
        status="ACTIVE",
    )
    db_session.add_all([u2, m2])
    await db_session.commit()

    token2, _ = create_access_token(admin_org2_id)
    org2_admin_headers = {
        "Authorization": f"Bearer {token2}",
        "X-Organization-ID": str(ORG_2_ID),
    }
    res_org2 = await async_client.get("/api/v1/audit-logs", headers=org2_admin_headers)
    assert res_org2.status_code == 200
    assert res_org2.json()["meta"]["total_count"] == 0  # Does not see ORG_1's audit entry


@pytest.mark.asyncio
async def test_health_probes(async_client: AsyncClient):
    """
    Test liveness and readiness health endpoints.
    """
    # Liveness
    live_res = await async_client.get("/api/v1/health/live")
    assert live_res.status_code == 200
    live_data = live_res.json()["data"]
    assert live_data["status"] == "alive"

    # Readiness
    ready_res = await async_client.get("/api/v1/health/ready")
    assert ready_res.status_code == 200
    ready_data = ready_res.json()["data"]
    assert ready_data["status"] == "ready"
    assert ready_data["checks"]["database"] == "connected"
    assert "redis" in ready_data["checks"]
    assert "storage" in ready_data["checks"]
