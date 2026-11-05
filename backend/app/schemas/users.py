"""Pydantic schemas for users, authentication, roles, and permissions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..models.User import AccountStatus


class UserBase(BaseModel):
    full_name: str = Field(..., max_length=255)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)
    status: Optional[AccountStatus] = AccountStatus.ACTIVE


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)
    status: Optional[AccountStatus] = None


class UserRead(UserBase):
    id: int
    status: AccountStatus
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class AccountVerificationCreate(BaseModel):
    user_id: int
    verification_type: str = Field(..., max_length=32)
    token_digest: str = Field(..., max_length=255)
    expires_at: datetime


class AccountVerificationRead(BaseModel):
    id: uuid.UUID
    user_id: int
    verification_type: str
    token_digest: str
    expires_at: datetime
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    is_active: bool = True


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RoleRead(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionBase(BaseModel):
    code: str = Field(..., max_length=128)
    description: Optional[str] = None
    is_active: bool = True


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionRead(PermissionBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RolePermissionCreate(BaseModel):
    role_id: int
    permission_id: uuid.UUID


class RolePermissionRead(BaseModel):
    id: uuid.UUID
    role_id: int
    permission_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class UserRoleCreate(BaseModel):
    user_id: int
    role_id: int


class UserRoleRead(BaseModel):
    id: int
    university_id: uuid.UUID
    user_id: int
    role_id: int
    assigned_by_id: Optional[int] = None
    assigned_at: datetime
    revoked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

