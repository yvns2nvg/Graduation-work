"""FastAPI 앱 진입점 - CORS, 라우터 등록, DB 초기화"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, shoes, download, websocket
from app.services.storage_service import ensure_storage_dirs

# ----- 로깅 설정 -----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ----- 앱 시작/종료 이벤트 -----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 DB 테이블 생성 + 스토리지 디렉토리 생성"""
    logger.info("🚀 서버 시작 - DB 테이블 및 스토리지 디렉토리 초기화")
    # 모델 import를 통해 Base에 등록
    import app.models  # noqa: F401
    await init_db()
    ensure_storage_dirs()
    yield
    logger.info("🛑 서버 종료")


# ----- FastAPI 앱 생성 -----
app = FastAPI(
    title="👟 Text-to-3D Shoe Platform API",
    description="텍스트를 기반으로 신발 이미지를 생성하고, TRELLIS 가우시안 스플래팅으로 3D 모델을 만드는 플랫폼",
    version="0.1.0",
    lifespan=lifespan,
)

# ----- CORS 미들웨어 (프론트엔드 연동용) -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계: 모든 출처 허용. 배포 시 프론트엔드 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- 라우터 등록 -----
app.include_router(auth.router)
app.include_router(shoes.router)
app.include_router(download.router)
app.include_router(websocket.router)


# ----- 기본 엔드포인트 -----
@app.get("/", tags=["상태"])
async def root():
    """API 서버 상태 확인"""
    return {
        "message": "👟 Text-to-3D Shoe Platform API",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health", tags=["상태"])
async def health_check():
    """헬스 체크"""
    from app.services.llm_service import check_llm_server_health
    from app.services.trellis_service import check_trellis_server_health

    return {
        "api_server": "healthy",
        "llm_server": await check_llm_server_health(),
        "trellis_server": await check_trellis_server_health(),
    }
