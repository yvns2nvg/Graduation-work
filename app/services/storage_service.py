"""파일 스토리지 서비스 - 로컬 저장 및 GCS(Google Cloud Storage) 버킷 저장 지원

- GCS_BUCKET_NAME 환경변수가 설정되면 → GCS 버킷에 파일 저장/조회/삭제
- 설정되지 않으면 → 기존 로컬 폴더(storage/) 저장 방식 유지
"""

import io
import os
import uuid
import logging
from pathlib import Path
from typing import Optional

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ===== 로컬 저장소 디렉토리 경로 (로컬 모드 전용) =====
IMAGES_DIR = Path(settings.STORAGE_PATH) / "images"
MODELS_3D_DIR = Path(settings.STORAGE_PATH) / "models_3d"

# ===== GCS 클라이언트 (클라우드 모드 전용) =====
_gcs_client = None
_gcs_bucket = None


def _get_gcs_bucket():
    """GCS 버킷 객체를 가져옴 (lazy initialization)"""
    global _gcs_client, _gcs_bucket
    if _gcs_bucket is None:
        from google.cloud import storage as gcs_storage
        _gcs_client = gcs_storage.Client()
        _gcs_bucket = _gcs_client.bucket(settings.GCS_BUCKET_NAME)
    return _gcs_bucket


# ===== 디렉토리 초기화 =====

def ensure_storage_dirs():
    """스토리지 디렉토리 생성 (로컬 모드에서만 필요)"""
    if not settings.is_cloud_storage:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        MODELS_3D_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("로컬 스토리지 디렉토리 초기화 완료")
    else:
        logger.info(f"GCS 버킷 모드: {settings.GCS_BUCKET_NAME}")


# ===== 이미지 저장 =====

def save_image(image_data: bytes, extension: str = ".png") -> str:
    """이미지 파일 저장

    Args:
        image_data: 이미지 바이너리 데이터
        extension: 파일 확장자

    Returns:
        저장된 파일의 상대 경로 (예: images/abc123.png)
    """
    filename = f"{uuid.uuid4().hex}{extension}"
    relative_path = f"images/{filename}"

    if settings.is_cloud_storage:
        bucket = _get_gcs_bucket()
        blob = bucket.blob(relative_path)
        blob.upload_from_string(image_data, content_type=f"image/{extension.lstrip('.')}")
        logger.info(f"이미지 GCS 저장: gs://{settings.GCS_BUCKET_NAME}/{relative_path}")
    else:
        ensure_storage_dirs()
        filepath = IMAGES_DIR / filename
        with open(filepath, "wb") as f:
            f.write(image_data)
        logger.info(f"이미지 로컬 저장: {filepath}")

    return relative_path


# ===== 3D 모델 저장 =====

def save_3d_model(model_data: bytes, extension: str = ".glb") -> str:
    """3D 모델 파일 저장

    Args:
        model_data: 3D 모델 바이너리 데이터
        extension: 파일 확장자 (.glb, .ply, .splat)

    Returns:
        저장된 파일의 상대 경로 (예: models_3d/abc123.glb)
    """
    filename = f"{uuid.uuid4().hex}{extension}"
    relative_path = f"models_3d/{filename}"

    if settings.is_cloud_storage:
        bucket = _get_gcs_bucket()
        blob = bucket.blob(relative_path)
        blob.upload_from_string(model_data, content_type="application/octet-stream")
        logger.info(f"3D 모델 GCS 저장: gs://{settings.GCS_BUCKET_NAME}/{relative_path}")
    else:
        ensure_storage_dirs()
        filepath = MODELS_3D_DIR / filename
        with open(filepath, "wb") as f:
            f.write(model_data)
        logger.info(f"3D 모델 로컬 저장: {filepath}")

    return relative_path


# ===== 파일 경로 / URL 조회 =====

def get_file_path(relative_path: str) -> Path:
    """상대 경로를 로컬 절대 경로로 변환 (로컬 모드 전용)

    Args:
        relative_path: 저장소 기준 상대 경로 (예: images/abc123.png)

    Returns:
        절대 파일 경로
    """
    return Path(settings.STORAGE_PATH) / relative_path


def get_public_url(relative_path: str) -> str:
    """파일의 공개 URL 반환

    - GCS 모드: GCS 공개 URL 반환
    - 로컬 모드: API 서버 경유 경로 반환
    """
    if settings.is_cloud_storage:
        return f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{relative_path}"
    else:
        return relative_path


def get_file_bytes(relative_path: str) -> Optional[bytes]:
    """파일 바이너리 데이터 가져오기

    - GCS 모드: 버킷에서 다운로드
    - 로컬 모드: 로컬 파일 읽기

    Returns:
        파일 바이너리 데이터 또는 None (파일 없음)
    """
    if settings.is_cloud_storage:
        try:
            bucket = _get_gcs_bucket()
            blob = bucket.blob(relative_path)
            if blob.exists():
                return blob.download_as_bytes()
            return None
        except Exception as e:
            logger.error(f"GCS 파일 다운로드 실패: {e}")
            return None
    else:
        filepath = get_file_path(relative_path)
        if filepath.exists():
            with open(filepath, "rb") as f:
                return f.read()
        return None


# ===== 파일 존재 확인 =====

def file_exists(relative_path: str) -> bool:
    """파일 존재 여부 확인"""
    if settings.is_cloud_storage:
        try:
            bucket = _get_gcs_bucket()
            blob = bucket.blob(relative_path)
            return blob.exists()
        except Exception:
            return False
    else:
        return get_file_path(relative_path).exists()


# ===== 파일 삭제 =====

def delete_file(relative_path: str) -> bool:
    """파일 삭제

    Returns:
        삭제 성공 여부
    """
    if settings.is_cloud_storage:
        try:
            bucket = _get_gcs_bucket()
            blob = bucket.blob(relative_path)
            if blob.exists():
                blob.delete()
                logger.info(f"GCS 파일 삭제: gs://{settings.GCS_BUCKET_NAME}/{relative_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"GCS 파일 삭제 실패: {e}")
            return False
    else:
        filepath = get_file_path(relative_path)
        if filepath.exists():
            os.remove(filepath)
            logger.info(f"로컬 파일 삭제: {filepath}")
            return True
        return False
