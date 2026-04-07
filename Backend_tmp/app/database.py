"""비동기 SQLAlchemy 데이터베이스 설정"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# ----- 비동기 엔진 생성 -----
# SQLite: connect_args로 check_same_thread 비활성화
# PostgreSQL (Cloud SQL): 추가 옵션 없이 생성
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL (Cloud Run + Cloud SQL 등)
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # 연결 유효성 사전 체크 (Cloud SQL 연결 끊김 방지)
    )

# ----- 비동기 세션 팩토리 -----
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 기본 클래스"""
    pass


async def get_db():
    """FastAPI 의존성 주입용 DB 세션 제공 함수"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """애플리케이션 시작 시 DB 테이블 자동 생성"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
