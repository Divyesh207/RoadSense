import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import pytest
from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.auth import (
    OrgContext,
    get_current_org_context,
    require_permission,
    require_role,
    verify_org_isolation,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.main import app
from app.models.history import AuditLog
from app.models.identity import RefreshToken
from tests.conftest import (
    AUTHORITY_USER_ID,
    INSPECTOR_USER_ID,
    ORG_1_ID,
    ORG_2_ID,
)

# Router for RBAC and Multi-Tenant Isolation route verification
rbac_router = APIRouter(prefix="/api/v1/test-rbac", tags=["Test RBAC"])


@rbac_router.get("/admin-only")
async def rbac_endpoint_admin_only(
    org_ctx: Annotated[OrgContext, Depends(require_role(["ADMINISTRATOR"]))],
):
    return {"message": "Welcome Admin", "role": org_ctx.role.code}


@rbac_router.get("/road-management")
async def rbac_endpoint_road_mgmt(
    org_ctx: Annotated[OrgContext, Depends(require_role(["ADMINISTRATOR", "ROAD_AUTHORITY"]))],
):
    return {"message": "Access granted", "org_id": str(org_ctx.organization_id)}


@rbac_router.get("/permission-roads-create")
async def rbac_endpoint_permission_roads_create(
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:create"))],
):
    return {"message": "Can create roads", "user_id": str(org_ctx.membership.user_id)}


@rbac_router.get("/tenant-resource/{resource_org_id}")
async def rbac_endpoint_tenant_resource(
    resource_org_id: uuid.UUID,
    org_ctx: Annotated[OrgContext, Depends(get_current_org_context)],
):
    verify_org_isolation(resource_org_id, org_ctx.organization_id)
    return {"message": "Resource accessed", "org_id": str(org_ctx.organization_id)}


# Include test router on app
app.include_router(rbac_router)


# --- 1. Password Hashing Tests ---

def test_password_hashing_and_verification():
    raw_pass = "ComplexP@ssw0rd!2026"
    hashed = hash_password(raw_pass)

    assert hashed != raw_pass
    assert hashed.startswith(("$2b$", "$2a$"))
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


# --- 2. JWT Access Token Tests ---

def test_access_token_creation_and_decoding():
    user_id = uuid.uuid4()
    token, expires_in = create_access_token(user_id)

    assert isinstance(token, str)
    assert expires_in == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_expired_token_handling():
    user_id = uuid.uuid4()
    expired_payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=10),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=20),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_invalid_token_signature():
    user_id = uuid.uuid4()
    tampered_token = jwt.encode(
        {"sub": str(user_id)},
        "wrong_secret_key_12345678901234567890",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered_token)


# --- 3. Login Endpoint Tests ---

@pytest.mark.asyncio
async def test_login_success(async_client, db_session):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "authority@example.com", "password": "AuthoritySecret123!"},
        headers={"User-Agent": "TestClient/1.0"},
    )
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["success"] is True
    data = res_json["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Verify refresh token hash stored in DB
    refresh_hash = hash_token(data["refresh_token"])
    stmt = select(RefreshToken).where(RefreshToken.token_hash == refresh_hash)
    token_record = (await db_session.execute(stmt)).scalar_one_or_none()
    assert token_record is not None
    assert token_record.user_id == AUTHORITY_USER_ID
    assert token_record.revoked_at is None

    # Verify audit log recorded
    audit_stmt = select(AuditLog).where(
        AuditLog.actor_user_id == AUTHORITY_USER_ID,
        AuditLog.action == "USER_LOGIN",
    )
    audit = (await db_session.execute(audit_stmt)).scalar_one_or_none()
    assert audit is not None


@pytest.mark.asyncio
async def test_login_invalid_password(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "authority@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    res_json = response.json()
    assert res_json["success"] is False
    assert res_json["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown_user_999@example.com", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    res_json = response.json()
    assert res_json["success"] is False
    assert res_json["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_inactive_user(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "InactiveSecret123!"},
    )
    assert response.status_code == 401
    res_json = response.json()
    assert res_json["success"] is False
    assert res_json["error"]["code"] == "AUTHENTICATION_REQUIRED"


# --- 4. Refresh Token Lifecycle Tests ---

@pytest.mark.asyncio
async def test_refresh_token_lifecycle_and_rotation(async_client, db_session):
    # Step 1: Login to get initial tokens
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@example.com", "password": "InspectorSecret123!"},
    )
    assert login_resp.status_code == 200
    initial_refresh = login_resp.json()["data"]["refresh_token"]

    # Step 2: Use refresh token to obtain a new pair
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert refresh_resp.status_code == 200
    refreshed_data = refresh_resp.json()["data"]
    new_refresh = refreshed_data["refresh_token"]
    assert new_refresh != initial_refresh
    assert "access_token" in refreshed_data

    # Step 3: Verify the original refresh token is now revoked in the DB
    old_hash = hash_token(initial_refresh)
    old_record = (await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == old_hash))).scalar_one()
    assert old_record.revoked_at is not None

    # Step 4: Reusing the old rotated refresh token must fail with 401
    replay_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert replay_resp.status_code == 401
    assert replay_resp.json()["error"]["code"] == "TOKEN_INVALID"

    # Step 5: The new refresh token should be usable
    valid_second_refresh = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert valid_second_refresh.status_code == 200


@pytest.mark.asyncio
async def test_refresh_expired_token(async_client, db_session):
    # Create an already expired refresh token in DB
    raw_token, token_hash = generate_refresh_token()
    expired_record = RefreshToken(
        id=uuid.uuid4(),
        user_id=INSPECTOR_USER_ID,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        created_at=datetime.now(timezone.utc) - timedelta(days=8),
    )
    db_session.add(expired_record)
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": raw_token},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


# --- 5. Current User (GET /api/v1/auth/me) Tests ---

@pytest.mark.asyncio
async def test_get_current_user_profile(async_client):
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "authority@example.com", "password": "AuthoritySecret123!"},
    )
    access_token = login_resp.json()["data"]["access_token"]

    # Request /me with valid token
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    user_data = me_resp.json()["data"]

    assert user_data["email"] == "authority@example.com"
    assert user_data["full_name"] == "Authority Officer"
    assert user_data["is_active"] is True
    assert len(user_data["organizations"]) >= 1

    org_membership = user_data["organizations"][0]
    assert org_membership["organization_id"] == str(ORG_1_ID)
    assert org_membership["role_code"] == "ROAD_AUTHORITY"
    assert "roads:create" in org_membership["permissions"]


@pytest.mark.asyncio
async def test_me_unauthenticated(async_client):
    # Request without Authorization header
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_me_malformed_token(async_client):
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer malformed.or.garbage.token"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "TOKEN_INVALID"


# --- 6. Logout Endpoint Tests ---

@pytest.mark.asyncio
async def test_logout_specific_token(async_client, db_session):
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "crew@example.com", "password": "CrewSecret123!"},
    )
    tokens = login_resp.json()["data"]

    # Logout revoking specific refresh token
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["data"]["message"] == "Logged out successfully."

    # Verify refresh token is revoked
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_sessions(async_client, db_session):
    # Perform two logins for same user to create two active sessions
    login1 = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "crew@example.com", "password": "CrewSecret123!"},
    )
    login2 = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "crew@example.com", "password": "CrewSecret123!"},
    )
    token1 = login1.json()["data"]["refresh_token"]
    token2 = login2.json()["data"]["refresh_token"]
    access_token = login2.json()["data"]["access_token"]

    # Logout without refresh_token revokes ALL active refresh tokens for user
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={},
    )
    assert logout_resp.status_code == 200

    # Both refresh tokens must now be rejected
    r1 = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    r2 = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": token2})
    assert r1.status_code == 401
    assert r2.status_code == 401


# --- 7. RBAC & Role Authorization Tests ---

@pytest.mark.asyncio
async def test_role_authorization_allowed(async_client):
    # Admin login
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminSecret123!"},
    )
    admin_token = admin_login.json()["data"]["access_token"]

    # Admin accesses /admin-only
    resp = await async_client.get(
        "/api/v1/test-rbac/admin-only",
        headers={"Authorization": f"Bearer {admin_token}", "X-Organization-ID": str(ORG_1_ID)},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "ADMINISTRATOR"


@pytest.mark.asyncio
async def test_role_authorization_forbidden(async_client):
    # Inspector login
    insp_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@example.com", "password": "InspectorSecret123!"},
    )
    insp_token = insp_login.json()["data"]["access_token"]

    # Inspector attempts /admin-only -> 403 FORBIDDEN
    resp = await async_client.get(
        "/api/v1/test-rbac/admin-only",
        headers={"Authorization": f"Bearer {insp_token}", "X-Organization-ID": str(ORG_1_ID)},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


# --- 8. RBAC & Permission Authorization Tests ---

@pytest.mark.asyncio
async def test_permission_authorization_allowed(async_client):
    # Road Authority has permission "roads:create"
    auth_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "authority@example.com", "password": "AuthoritySecret123!"},
    )
    token = auth_login.json()["data"]["access_token"]

    resp = await async_client.get(
        "/api/v1/test-rbac/permission-roads-create",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Can create roads"


@pytest.mark.asyncio
async def test_permission_authorization_denied(async_client):
    # Field Inspector does NOT have "roads:create"
    insp_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@example.com", "password": "InspectorSecret123!"},
    )
    token = insp_login.json()["data"]["access_token"]

    resp = await async_client.get(
        "/api/v1/test-rbac/permission-roads-create",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_bypasses_specific_permission_check(async_client):
    # Administrator role implicitly passes permission checks
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminSecret123!"},
    )
    token = admin_login.json()["data"]["access_token"]

    resp = await async_client.get(
        "/api/v1/test-rbac/permission-roads-create",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)},
    )
    assert resp.status_code == 200


# --- 9. Multi-Tenant Context & Organization Isolation Tests ---

@pytest.mark.asyncio
async def test_valid_tenant_context_header(async_client):
    auth_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "authority@example.com", "password": "AuthoritySecret123!"},
    )
    token = auth_login.json()["data"]["access_token"]

    resp = await async_client.get(
        "/api/v1/test-rbac/road-management",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)},
    )
    assert resp.status_code == 200
    assert resp.json()["org_id"] == str(ORG_1_ID)


@pytest.mark.asyncio
async def test_forbidden_cross_organization_header(async_client):
    # User is member of Org 1 only
    auth_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "authority@example.com", "password": "AuthoritySecret123!"},
    )
    token = auth_login.json()["data"]["access_token"]

    # Client tries to claim membership in Org 2 -> Server validates membership in DB and rejects with 403
    resp = await async_client.get(
        "/api/v1/test-rbac/road-management",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_2_ID)},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_cross_tenant_resource_isolation(async_client):
    auth_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "authority@example.com", "password": "AuthoritySecret123!"},
    )
    token = auth_login.json()["data"]["access_token"]

    # Accessing resource belonging to user's org (Org 1) -> 200 OK
    valid_resp = await async_client.get(
        f"/api/v1/test-rbac/tenant-resource/{ORG_1_ID}",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)},
    )
    assert valid_resp.status_code == 200

    # Accessing resource belonging to another org (Org 2) -> 403 ORGANIZATION_ACCESS_DENIED
    forbidden_resp = await async_client.get(
        f"/api/v1/test-rbac/tenant-resource/{ORG_2_ID}",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)},
    )
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"
