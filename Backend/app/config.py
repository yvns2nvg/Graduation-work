"""환경 설정 관리 모듈"""

from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 환경 설정"""

    # SQLite 데이터베이스 설정 (개발 환경용)
    # 로컬: sqlite+aiosqlite:///./text_to_3d.db
    # GCS 사용 시: 클라우드 SQL 등 다른 DB URL 사용 고려
    DATABASE_URL: str = "sqlite+aiosqlite:///./text_to_3d.db"

    # ----- JWT -----
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ----- LLM Server (AI팀 - 로컬 모델, Linux Cloud GPU) -----
    LLM_SERVER_URL: str = "http://localhost:8001"
    LLM_REQUEST_TIMEOUT: int = 120

    # ----- TRELLIS 3D Server (3D팀 - Gaussian Splatting) -----
    TRELLIS_SERVER_URL: str = "http://localhost:8002"
    TRELLIS_REQUEST_TIMEOUT: int = 300

    # ----- File Storage -----
    # 로컬 개발: 로컬 폴더 사용 (STORAGE_PATH)
    # Cloud Run: GCS 버킷 사용 (GCS_BUCKET_NAME 설정 시 자동 전환)
    STORAGE_PATH: str = "./storage"
    GCS_BUCKET_NAME: Optional[str] = None  # 설정하면 GCS 모드로 전환

    # ----- Cloud Run 환경 판별 -----
    # Cloud Run은 자동으로 PORT 환경변수를 주입함
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def is_cloud_storage(self) -> bool:
        """GCS 버킷이 설정되어 있으면 클라우드 스토리지 모드"""
        return self.GCS_BUCKET_NAME is not None


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()
