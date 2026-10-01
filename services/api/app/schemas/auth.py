import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponseData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class UserOrganizationMembershipInfo(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_code: str
    role_id: uuid.UUID
    role_code: str
    status: str
    permissions: list[str] = Field(default_factory=list)


class CurrentUserResponseData(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None = None
    is_active: bool
    organizations: list[UserOrganizationMembershipInfo] = Field(default_factory=list)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class MessageResponseData(BaseModel):
    message: str
