"""파일 스토리지 서비스 - 이미지 및 3D 모델 파일 저장/조회/삭제"""

import os
import uuid
import logging
from pathlib import Path

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 저장소 디렉토리 경로
IMAGES_DIR = Path(settings.STORAGE_PATH) / "images"
MODELS_3D_DIR = Path(settings.STORAGE_PATH) / "models_3d"


def ensure_storage_dirs():
    """스토리지 디렉토리 생성 (없으면 자동 생성)"""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_3D_DIR.mkdir(parents=True, exist_ok=True)


def save_image(image_data: bytes, extension: str = ".png") -> str:
    """이미지 파일 저장

    Args:
        image_data: 이미지 바이너리 데이터
        extension: 파일 확장자

    Returns:
        저장된 파일의 상대 경로 (예: images/abc123.png)
    """
    ensure_storage_dirs()
    filename = f"{uuid.uuid4().hex}{extension}"
    filepath = IMAGES_DIR / filename

    with open(filepath, "wb") as f:
        f.write(image_data)

    logger.info(f"이미지 저장: {filepath}")
    return f"images/{filename}"


def save_3d_model(model_data: bytes, extension: str = ".glb") -> str:
    """3D 모델 파일 저장

    Args:
        model_data: 3D 모델 바이너리 데이터
        extension: 파일 확장자 (.glb, .ply, .splat)

    Returns:
        저장된 파일의 상대 경로 (예: models_3d/abc123.glb)
    """
    ensure_storage_dirs()
    filename = f"{uuid.uuid4().hex}{extension}"
    filepath = MODELS_3D_DIR / filename

    with open(filepath, "wb") as f:
        f.write(model_data)

    logger.info(f"3D 모델 저장: {filepath}")
    return f"models_3d/{filename}"


def get_file_path(relative_path: str) -> Path:
    """상대 경로를 절대 경로로 변환

    Args:
        relative_path: 저장소 기준 상대 경로 (예: images/abc123.png)

    Returns:
        절대 파일 경로
    """
    return Path(settings.STORAGE_PATH) / relative_path


def file_exists(relative_path: str) -> bool:
    """파일 존재 여부 확인"""
    return get_file_path(relative_path).exists()


def delete_file(relative_path: str) -> bool:
    """파일 삭제

    Returns:
        삭제 성공 여부
    """
    filepath = get_file_path(relative_path)
    if filepath.exists():
        os.remove(filepath)
        logger.info(f"파일 삭제: {filepath}")
        return True
    return False
