from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class UserCreate(UserBase):
    openid: str
    unionid: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    openid: str
    created_at: datetime

    class Config:
        from_attributes = True
