import pytest
from sqlalchemy import func, select

from app.bootstrap import bootstrap_admin
from app.core.security import verify_password
from app.models.identity import OrganizationMembership, User


@pytest.mark.asyncio
async def test_bootstrap_creates_admin_who_can_log_in_and_is_idempotent(async_client, db_session):
    first = await bootstrap_admin(
        db_session, "DEMO", "Demo Road Authority", "MUNICIPAL", "Admin@Demo.example", "a-long-demo-password"
    )
    assert first.created_organization and first.created_user and first.created_membership

    login = await async_client.post(
        "/api/v1/auth/login", json={"email": "admin@demo.example", "password": "a-long-demo-password"}
    )
    assert login.status_code == 200, login.text
    headers = {
        "Authorization": f"Bearer {login.json()['data']['access_token']}",
        "X-Organization-ID": str(first.organization_id),
    }
    # ADMINISTRATOR has implicit full access
    assert (await async_client.get("/api/v1/roads", headers=headers)).status_code == 200

    again = await bootstrap_admin(
        db_session, "DEMO", "Demo Road Authority", "MUNICIPAL", "admin@demo.example", "a-different-password!"
    )
    assert not (again.created_organization or again.created_user or again.created_membership)
    user = (await db_session.execute(select(User).where(User.email == "admin@demo.example"))).scalar_one()
    assert verify_password("a-long-demo-password", user.password_hash)  # never overwritten
    count = (
        await db_session.execute(select(func.count()).select_from(OrganizationMembership).where(OrganizationMembership.user_id == user.id))
    ).scalar()
    assert count == 1


@pytest.mark.asyncio
async def test_bootstrap_rejects_short_password(db_session):
    with pytest.raises(ValueError):
        await bootstrap_admin(db_session, "DEMO", "Demo", "MUNICIPAL", "a@b.example", "short")


@pytest.mark.asyncio
@pytest.mark.parametrize("email", ["admin@demo-roads.test", "not-an-email", "admin@localhost"])
async def test_bootstrap_rejects_email_that_login_would_reject(db_session, email):
    # LoginRequest uses EmailStr; reserved TLDs such as .test would create an admin who can never log in.
    with pytest.raises(ValueError, match="Invalid admin email"):
        await bootstrap_admin(db_session, "DEMO", "Demo", "MUNICIPAL", email, "a-long-demo-password")
    assert (await db_session.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none() is None
