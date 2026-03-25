"""TRELLIS 3D 변환 서버 통신 서비스

3D팀의 TRELLIS 서버는:
- 가우시안 스플래팅(Gaussian Splatting) 기반 이미지 → 3D 변환
- 리눅스 클라우드 GPU 서버에서 운영
- 입력: 이미지 파일 → 출력: .glb 또는 .ply 3D 모델 파일
"""

import logging
from pathlib import Path

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def request_3d_conversion(image_path: str) -> dict:
    """TRELLIS 서버에 이미지 → 3D 모델 변환 요청 (로컬 파일 경로 기반)

    Args:
        image_path: 로컬에 저장된 이미지 파일 경로

    Returns:
        dict: {
            "success": bool,
            "model_data": bytes | None,   # 3D 모델 바이너리 데이터
            "file_extension": str | None, # 파일 확장자 (.glb, .ply 등)
            "error": str | None
        }
    """
    try:
        image_file = Path(image_path)
        if not image_file.exists():
            return {
                "success": False,
                "model_data": None,
                "file_extension": None,
                "error": f"이미지 파일을 찾을 수 없습니다: {image_path}",
            }

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        return await _send_to_trellis(image_bytes, image_file.name)

    except Exception as e:
        logger.error(f"TRELLIS 서버 통신 중 예외 발생: {e}")
        return {
            "success": False,
            "model_data": None,
            "file_extension": None,
            "error": str(e),
        }


async def request_3d_conversion_from_bytes(image_bytes: bytes, filename: str = "image.png") -> dict:
    """TRELLIS 서버에 이미지 → 3D 모델 변환 요청 (바이트 데이터 기반, GCS 호환)

    Args:
        image_bytes: 이미지 바이너리 데이터
        filename: 파일명 (TRELLIS 서버 전송용)

    Returns:
        dict: {
            "success": bool,
            "model_data": bytes | None,
            "file_extension": str | None,
            "error": str | None
        }
    """
    return await _send_to_trellis(image_bytes, filename)


async def _send_to_trellis(image_bytes: bytes, filename: str) -> dict:
    """TRELLIS 서버에 이미지 데이터 전송하는 내부 함수"""
    try:
        async with httpx.AsyncClient(timeout=settings.TRELLIS_REQUEST_TIMEOUT) as client:
            # 이미지 파일을 multipart/form-data로 전송
            files = {"image": (filename, image_bytes, "image/png")}
            response = await client.post(
                f"{settings.TRELLIS_SERVER_URL}/convert",
                files=files,
            )

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")

                # 3D 모델 파일이 바이너리로 올 경우
                if "application/octet-stream" in content_type or "model" in content_type:
                    # Content-Disposition 헤더에서 파일 확장자 추출
                    content_disp = response.headers.get("content-disposition", "")
                    if ".ply" in content_disp:
                        ext = ".ply"
                    elif ".splat" in content_disp:
                        ext = ".splat"
                    else:
                        ext = ".glb"  # 기본값

                    return {
                        "success": True,
                        "model_data": response.content,
                        "file_extension": ext,
                        "error": None,
                    }
                else:
                    # JSON 응답인 경우 (다운로드 URL 포함)
                    data = response.json()
                    return {
                        "success": True,
                        "model_data": data,
                        "file_extension": ".glb",
                        "error": None,
                    }
            else:
                logger.error(f"TRELLIS 서버 오류: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "model_data": None,
                    "file_extension": None,
                    "error": f"TRELLIS 서버 응답 오류: {response.status_code}",
                }

    except httpx.TimeoutException:
        logger.error("TRELLIS 서버 요청 타임아웃")
        return {
            "success": False,
            "model_data": None,
            "file_extension": None,
            "error": "TRELLIS 서버 응답 시간 초과 (3D 변환에 시간이 오래 소요될 수 있습니다)",
        }
    except httpx.ConnectError:
        logger.error(f"TRELLIS 서버 연결 실패: {settings.TRELLIS_SERVER_URL}")
        return {
            "success": False,
            "model_data": None,
            "file_extension": None,
            "error": "TRELLIS 서버에 연결할 수 없습니다",
        }
    except Exception as e:
        logger.error(f"TRELLIS 서버 통신 중 예외 발생: {e}")
        return {
            "success": False,
            "model_data": None,
            "file_extension": None,
            "error": str(e),
        }


async def check_trellis_server_health() -> bool:
    """TRELLIS 서버 상태 확인 (헬스 체크)"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.TRELLIS_SERVER_URL}/health")
            return response.status_code == 200
    except Exception:
        return False
