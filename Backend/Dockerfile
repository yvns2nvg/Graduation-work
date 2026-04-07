# ========================================
# Cloud Run 배포용 Dockerfile
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

# Cloud Run은 PORT 환경변수를 자동 주입함 (기본 8080)
ENV PORT=8080

# uvicorn으로 FastAPI 서버 실행
# Cloud Run은 $PORT 환경변수로 포트를 전달하므로 이를 사용
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
