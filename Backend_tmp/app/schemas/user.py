"""사용자 관련 Pydantic 스키마 (요청/응답 데이터 검증)"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ===== 요청 스키마 =====

class UserCreate(BaseModel):
    """회원가입 요청"""
    email: EmailStr
    password: str = Field(..., min_length=6, description="비밀번호 (최소 6자)")
    nickname: Optional[str] = Field(None, max_length=100, description="닉네임")


class UserLogin(BaseModel):
    """로그인 요청"""
    email: EmailStr
    password: str


# ===== 응답 스키마 =====

class UserResponse(BaseModel):
    """사용자 정보 응답"""
    id: int
    email: str
    nickname: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT 토큰 응답"""
    access_token: str
    token_type: str = "bearer"
