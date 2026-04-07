# ========================================
# Render.com 배포용 Dockerfile
# ========================================
FROM python:3.11-slim

# 시스템 패키지 업데이트
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 먼저 설치 (Docker 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# storage 디렉토리 생성 (로컬 모드 폴백용)
RUN mkdir -p storage/images storage/models_3d

# Render는 PORT 환경변수를 자동 주입함 (기본 10000)
ENV PORT=10000

# uvicorn으로 FastAPI 서버 실행
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
