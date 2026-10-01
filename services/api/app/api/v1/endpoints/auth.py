from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_token,
    verify_password,
)
from app.models.history import AuditLog
from app.models.identity import (
    OrganizationMembership,
    RefreshToken,
    Role,
    User,
)
from app.schemas.auth import (
    CurrentUserResponseData,
    LoginRequest,
    LogoutRequest,
    MessageResponseData,
    RefreshTokenRequest,
    TokenResponseData,
    UserOrganizationMembershipInfo,
)
from app.schemas.common import ResponseEnvelope, ResponseMeta

router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt



@router.post(
    "/login",
    response_model=ResponseEnvelope[TokenResponseData],
    summary="Authenticate user and return JWT access & refresh tokens",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[TokenResponseData]:
    request_id = getattr(request.state, "request_id", None)

    # Case-insensitive email lookup
    stmt = select(User).where(func.lower(User.email) == payload.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Account has been deactivated. Please contact your administrator.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    user.last_login_at = utc_now()

    # Generate tokens
    access_token, expires_in = create_access_token(user.id)
    raw_refresh_token, refresh_hash = generate_refresh_token()

    # Persist refresh token hash
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        device_identifier=request.headers.get("User-Agent"),
        expires_at=utc_now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        created_at=utc_now(),
        last_used_at=utc_now(),
    )
    db.add(refresh_record)

    # Security Audit Log
    client_ip = request.client.host if request.client else None
    audit_entry = AuditLog(
        actor_user_id=user.id,
        action="USER_LOGIN",
        entity_type="users",
        entity_id=user.id,
        request_id=request_id,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent"),
        metadata_={"email": user.email},
        created_at=utc_now(),
    )
    db.add(audit_entry)

    await db.commit()

    return ResponseEnvelope(
        success=True,
        data=TokenResponseData(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        ),
        meta=ResponseMeta(request_id=request_id),
    )


@router.post(
    "/refresh",
    response_model=ResponseEnvelope[TokenResponseData],
    summary="Rotate refresh token and issue new access token",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[TokenResponseData]:
    request_id = getattr(request.state, "request_id", None)
    incoming_hash = hash_token(payload.refresh_token)

    stmt = select(RefreshToken).where(RefreshToken.token_hash == incoming_hash)
    result = await db.execute(stmt)
    token_record = result.scalar_one_or_none()

    if token_record is None or token_record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_INVALID",
                "message": "Invalid or revoked refresh token.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if ensure_utc(token_record.expires_at) < utc_now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Refresh token has expired.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_result = await db.execute(select(User).where(User.id == token_record.user_id))
    user = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "User account is invalid or inactive.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Invalidate current refresh token (rotation)
    token_record.revoked_at = utc_now()

    # Issue new access token and new rotated refresh token
    access_token, expires_in = create_access_token(user.id)
    new_raw_refresh, new_refresh_hash = generate_refresh_token()

    new_refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=new_refresh_hash,
        device_identifier=request.headers.get("User-Agent"),
        expires_at=utc_now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        created_at=utc_now(),
        last_used_at=utc_now(),
    )
    db.add(new_refresh_record)
    await db.commit()

    return ResponseEnvelope(
        success=True,
        data=TokenResponseData(
            access_token=access_token,
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=expires_in,
        ),
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/me",
    response_model=ResponseEnvelope[CurrentUserResponseData],
    summary="Get current authenticated user profile and organization memberships",
)
async def get_current_user_profile(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[CurrentUserResponseData]:
    request_id = getattr(request.state, "request_id", None)

    # Load active memberships with org and role permissions
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
    result = await db.execute(stmt)
    memberships = result.scalars().all()

    org_list: list[UserOrganizationMembershipInfo] = []
    for m in memberships:
        permissions = [p.code for p in m.role.permissions]
        org_list.append(
            UserOrganizationMembershipInfo(
                organization_id=m.organization.id,
                organization_name=m.organization.name,
                organization_code=m.organization.code,
                role_id=m.role.id,
                role_code=m.role.code,
                status=m.status,
                permissions=permissions,
            )
        )

    return ResponseEnvelope(
        success=True,
        data=CurrentUserResponseData(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            phone=current_user.phone,
            is_active=current_user.is_active,
            organizations=org_list,
        ),
        meta=ResponseMeta(request_id=request_id),
    )


@router.post(
    "/logout",
    response_model=ResponseEnvelope[MessageResponseData],
    summary="Invalidate active session/refresh token",
)
async def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[MessageResponseData]:
    request_id = getattr(request.state, "request_id", None)

    if payload.refresh_token:
        # Revoke specific refresh token
        target_hash = hash_token(payload.refresh_token)
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.token_hash == target_hash,
        )
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        if token_record and token_record.revoked_at is None:
            token_record.revoked_at = utc_now()
    else:
        # Revoke all active refresh tokens for this user
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        result = await db.execute(stmt)
        for token_record in result.scalars().all():
            token_record.revoked_at = utc_now()

    await db.commit()

    return ResponseEnvelope(
        success=True,
        data=MessageResponseData(message="Logged out successfully."),
        meta=ResponseMeta(request_id=request_id),
    )
