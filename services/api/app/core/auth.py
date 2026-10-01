import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.identity import (
    Organization,
    OrganizationMembership,
    Role,
    User,
)

security_bearer = HTTPBearer(auto_error=False)


@dataclass
class OrgContext:
    organization_id: uuid.UUID
    organization: Organization
    membership: OrganizationMembership
    role: Role
    permissions: set[str]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate Bearer JWT access token and return the authenticated User."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication credentials were not provided.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Authentication token has expired.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_INVALID",
                "message": "Invalid authentication token.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "Invalid token subject."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALID", "message": "Malformed user identifier in token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_REQUIRED", "message": "User account not found."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_REQUIRED", "message": "User account is inactive or suspended."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_org_context(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_organization_id: Annotated[str | None, Header(alias="X-Organization-ID")] = None,
) -> OrgContext:
    """
    Resolve the active organization context for the authenticated user.
    Server-side validation guarantees the user is an ACTIVE member of the requested organization.
    """
    stmt = (
        select(OrganizationMembership)
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == "ACTIVE",
        )
        .options(
            selectinload(OrganizationMembership.organization),
            selectinload(OrganizationMembership.role).selectinload(Role.permissions),
        )
    )

    if x_organization_id:
        try:
            target_org_id = uuid.UUID(x_organization_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "VALIDATION_ERROR", "message": "Invalid X-Organization-ID format."},
            )
        stmt = stmt.where(OrganizationMembership.organization_id == target_org_id)

    result = await db.execute(stmt)
    memberships = result.scalars().all()

    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "User is not an active member of the specified organization.",
            },
        )

    # Use specified or first active membership
    active_membership = memberships[0]
    org = active_membership.organization
    role = active_membership.role

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "The organization account is inactive.",
            },
        )

    permissions = {p.code for p in role.permissions}

    return OrgContext(
        organization_id=org.id,
        organization=org,
        membership=active_membership,
        role=role,
        permissions=permissions,
    )


def require_role(allowed_roles: list[str]):
    """Factory dependency to enforce user roles in the active organization context."""
    normalized_allowed = {r.upper() for r in allowed_roles}

    async def role_checker(
        org_context: Annotated[OrgContext, Depends(get_current_org_context)],
    ) -> OrgContext:
        user_role = org_context.role.code.upper()
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Action requires one of the following roles: {', '.join(allowed_roles)}.",
                },
            )
        return org_context

    return role_checker


def require_permission(permission_code: str):
    """Factory dependency to enforce specific permissions in the active organization context."""

    async def permission_checker(
        org_context: Annotated[OrgContext, Depends(get_current_org_context)],
    ) -> OrgContext:
        # ADMINISTRATOR role has implicit full access
        if org_context.role.code.upper() == "ADMINISTRATOR":
            return org_context

        if permission_code not in org_context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Permission denied: '{permission_code}' is required for this operation.",
                },
            )
        return org_context

    return permission_checker


def verify_org_isolation(resource_org_id: uuid.UUID, current_org_id: uuid.UUID) -> None:
    """Enforce server-side organization boundary. Prevents horizontal privilege escalation."""
    if resource_org_id != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Cross-organization resource access is forbidden.",
            },
        )
