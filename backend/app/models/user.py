from __future__ import annotations
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    email: str
    full_name: str | None = None
    role: str  # admin | reviewer | viewer
    client_id: str | None = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str
    is_active: bool = True
    last_active_at: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str  # user_id
    email: str
    role: str
    client_id: str | None = None
    exp: int
