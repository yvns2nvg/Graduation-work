"""환경 설정 관리 모듈"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 환경 설정"""

    # ----- Database -----
    DATABASE_URL: str = "sqlite+aiosqlite:///./shoe_platform.db"

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
    STORAGE_PATH: str = "./storage"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()
