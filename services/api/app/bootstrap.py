"""
Idempotent bootstrap of the first organization and administrator.

A freshly migrated database has no organizations, roles or users, so nobody
can log in. This creates (or reuses) the organization, the ADMINISTRATOR
system role (which has implicit full access, see app.core.auth), the admin
user and an ACTIVE membership. It never overwrites an existing user's
password. Other roles' permission sets are not seeded here.

    BOOTSTRAP_ADMIN_PASSWORD=... python -m app.bootstrap \
        --org-code DEMO --org-name "Demo Road Authority" --admin-email admin@example.com
"""

import argparse
import asyncio
import os
import sys
import uuid
from dataclasses import dataclass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.identity import Organization, OrganizationMembership, Role, User

MIN_PASSWORD_LENGTH = 12
# Same validation as LoginRequest.email, so the created admin can actually log in.
_EMAIL_ADAPTER = TypeAdapter(EmailStr)


@dataclass
class BootstrapResult:
    organization_id: uuid.UUID
    user_id: uuid.UUID
    created_organization: bool
    created_user: bool
    created_membership: bool


async def bootstrap_admin(
    db: AsyncSession,
    org_code: str,
    org_name: str,
    org_type: str,
    admin_email: str,
    admin_password: str,
    admin_name: str = "Platform Administrator",
) -> BootstrapResult:
    if len(admin_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Admin password must be at least {MIN_PASSWORD_LENGTH} characters.")
    try:
        _EMAIL_ADAPTER.validate_python(admin_email.strip())
    except ValidationError as exc:
        raise ValueError(f"Invalid admin email '{admin_email}': {exc.errors()[0]['msg']}") from exc

    org = (await db.execute(select(Organization).where(Organization.code == org_code))).scalar_one_or_none()
    created_org = org is None
    if org is None:
        org = Organization(id=uuid.uuid4(), name=org_name, code=org_code, organization_type=org_type, is_active=True)
        db.add(org)

    role = (await db.execute(select(Role).where(Role.code == "ADMINISTRATOR"))).scalar_one_or_none()
    if role is None:
        role = Role(id=uuid.uuid4(), code="ADMINISTRATOR", name="Administrator", is_system_role=True)
        db.add(role)

    email = admin_email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    created_user = user is None
    if user is None:
        user = User(
            id=uuid.uuid4(), email=email, password_hash=hash_password(admin_password), full_name=admin_name, is_active=True
        )
        db.add(user)
    await db.flush()

    membership = (
        await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org.id, OrganizationMembership.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    created_membership = membership is None
    if membership is None:
        db.add(
            OrganizationMembership(
                id=uuid.uuid4(), organization_id=org.id, user_id=user.id, role_id=role.id, status="ACTIVE"
            )
        )
    await db.commit()
    return BootstrapResult(org.id, user.id, created_org, created_user, created_membership)


async def _main(args: argparse.Namespace) -> int:
    from app.core.database import AsyncSessionLocal, async_engine

    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not password:
        print("Set BOOTSTRAP_ADMIN_PASSWORD in the environment.", file=sys.stderr)
        return 2
    try:
        async with AsyncSessionLocal() as session:
            result = await bootstrap_admin(
                session, args.org_code, args.org_name, args.org_type, args.admin_email, password, args.admin_name
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        await async_engine.dispose()
    print(
        f"organization_id={result.organization_id} (created={result.created_organization}) "
        f"admin_user_id={result.user_id} (created={result.created_user}) "
        f"membership_created={result.created_membership}"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org-code", required=True)
    parser.add_argument("--org-name", required=True)
    parser.add_argument("--org-type", default="MUNICIPAL")
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-name", default="Platform Administrator")
    sys.exit(asyncio.run(_main(parser.parse_args())))


if __name__ == "__main__":
    main()
