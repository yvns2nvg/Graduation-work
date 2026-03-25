"""LLM 서버 통신 서비스 - AI팀의 이미지 생성 서버와 통신

AI팀의 LLM 서버는:
- 로컬 모델을 리눅스 클라우드 GPU 서버에서 운영
- OpenAI API 호환 규격 사용 (vLLM 또는 Ollama 기반)
"""

import logging
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def request_image_generation(prompt: str) -> dict:
    """LLM 서버에 신발 이미지 생성 요청

    Args:
        prompt: 사용자가 입력한 신발 설명 텍스트

    Returns:
        dict: {
            "success": bool,
            "image_data": bytes | None,  # 생성된 이미지 바이너리 데이터
            "error": str | None
        }
    """
    try:
        async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
            # OpenAI API 호환 규격으로 요청
            # AI팀과 정확한 엔드포인트 형식은 추후 조율 필요
            response = await client.post(
                f"{settings.LLM_SERVER_URL}/generate",
                json={
                    "prompt": prompt,
                    "type": "shoe",
                },
            )

            if response.status_code == 200:
                # 이미지 데이터가 바이너리(bytes)로 올 경우
                content_type = response.headers.get("content-type", "")

                if "image" in content_type:
                    return {
                        "success": True,
                        "image_data": response.content,
                        "error": None,
                    }
                else:
                    # JSON 응답인 경우 (이미지 URL 포함)
                    data = response.json()
                    return {
                        "success": True,
                        "image_data": data,
                        "error": None,
                    }
            else:
                logger.error(f"LLM 서버 오류: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "image_data": None,
                    "error": f"LLM 서버 응답 오류: {response.status_code}",
                }

    except httpx.TimeoutException:
        logger.error("LLM 서버 요청 타임아웃")
        return {
            "success": False,
            "image_data": None,
            "error": "LLM 서버 응답 시간 초과",
        }
    except httpx.ConnectError:
        logger.error(f"LLM 서버 연결 실패: {settings.LLM_SERVER_URL}")
        return {
            "success": False,
            "image_data": None,
            "error": "LLM 서버에 연결할 수 없습니다",
        }
    except Exception as e:
        logger.error(f"LLM 서버 통신 중 예외 발생: {e}")
        return {
            "success": False,
            "image_data": None,
            "error": str(e),
        }


async def check_llm_server_health() -> bool:
    """LLM 서버 상태 확인 (헬스 체크)"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.LLM_SERVER_URL}/health")
            return response.status_code == 200
    except Exception:
        return False
