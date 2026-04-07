"""생성 작업 관련 Pydantic 스키마 (요청/응답 데이터 검증)"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ===== 요청 스키마 =====

class GenerateRequest(BaseModel):
    """이미지 생성 요청"""
    prompt_text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="이미지/3D 생성을 위한 텍스트 프롬프트",
        examples=["파란색 사이버펑크 스타일의 의자"],
    )


class Convert3DRequest(BaseModel):
    """3D 변환 요청 (별도의 body 없이 path param만 사용할 수도 있지만, 확장성을 위해 정의)"""
    pass


# ===== 응답 스키마 =====

class GenerationResponse(BaseModel):
    """생성 작업 기본 응답"""
    id: int
    user_id: int
    prompt_text: str
    status: str
    image_url: Optional[str]
    model_3d_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerationStatusResponse(BaseModel):
    """작업 상태 조회 응답"""
    id: int
    status: str
    image_url: Optional[str] = None
    model_3d_url: Optional[str] = None

    model_config = {"from_attributes": True}


class GenerationListResponse(BaseModel):
    """생성 이력 목록 응답"""
    total: int
    items: list[GenerationResponse]
