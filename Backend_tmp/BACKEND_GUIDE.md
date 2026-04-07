# 🛠️ Backend 기술 가이드라인

> 백엔드 담당자를 위한 프레임워크 & 라이브러리 선정 가이드

---

## 🎯 담당 범위 요약

```
사용자 ↔ [Backend API] ↔ LLM 서버 (이미지 생성)
                       ↔ 3D 변환 서버 (Gaussian Splatting)
                       ↔ Database (사용자/이력 관리)
                       ↔ File Storage (이미지/3D 파일)
```

---

## 1. 웹 프레임워크: **FastAPI** (Python)

### 선정 이유
| 장점 | 설명 |
|------|------|
| **비동기 지원** | AI 모델 서버와의 통신에서 비동기 처리가 필수 (이미지 생성, 3D 변환은 시간이 오래 걸림) |
| **자동 API 문서** | Swagger UI 자동 생성 → 프론트엔드 팀과 협업 시 유리 |
| **Python 생태계** | AI/ML 팀과 같은 언어 → 통합 용이 |
| **빠른 성능** | ASGI 기반으로 Node.js 수준의 성능 |
| **타입 안정성** | Pydantic 기반 데이터 검증 |

```bash
pip install fastapi uvicorn[standard]
```

---

## 2. 데이터베이스: **PostgreSQL** + **SQLAlchemy**

### 선정 이유
- 복잡한 쿼리, JSON 데이터 저장 지원
- 확장성과 안정성이 뛰어남
- SQLAlchemy ORM으로 Python 코드로 DB 조작 가능

```bash
pip install sqlalchemy asyncpg alembic
```

| 패키지 | 용도 |
|--------|------|
| `sqlalchemy` | ORM (객체-관계 매핑) |
| `asyncpg` | PostgreSQL 비동기 드라이버 |
| `alembic` | DB 마이그레이션 관리 |

---

## 3. 인증: **JWT** (JSON Web Token)

```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

| 패키지 | 용도 |
|--------|------|
| `python-jose` | JWT 토큰 생성/검증 |
| `passlib` | 비밀번호 해싱 (bcrypt) |

### 인증 흐름
```
1. 회원가입 → 비밀번호 bcrypt 해싱 → DB 저장
2. 로그인 → 비밀번호 검증 → JWT Access Token 발급
3. API 요청 → Authorization 헤더에 JWT 포함 → 서버에서 검증
```

---

## 4. 외부 서버 통신: **httpx** (비동기 HTTP 클라이언트)

AI 팀의 LLM 서버, 3D 변환 서버와 통신할 때 사용

```bash
pip install httpx
```

### 사용 예시
```python
import httpx

async def request_image_generation(prompt: str) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://llm-server:8000/generate",
            json={"prompt": prompt}
        )
        return response.json()
```

---

## 5. 비동기 작업 큐: **Celery** + **Redis**

이미지 생성, 3D 변환은 수 초~수 분 소요 → 비동기 작업 큐 필수

```bash
pip install celery redis
```

| 구성 요소 | 역할 |
|-----------|------|
| **Celery** | 백그라운드 작업 실행 (이미지 생성 요청, 3D 변환 요청) |
| **Redis** | 메시지 브로커 + 작업 상태 캐싱 |

### 작업 흐름
```
1. 사용자 요청 → API 서버가 Celery 태스크 생성
2. Celery Worker가 LLM 서버에 이미지 생성 요청
3. 생성 완료 → DB 업데이트 (status: image_done)
4. 사용자가 상태 조회 API로 폴링 / WebSocket으로 알림
```

---

## 6. 실시간 알림 (선택): **WebSocket**

FastAPI 내장 WebSocket 지원으로 작업 완료 알림 전송 가능

```python
from fastapi import WebSocket

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    # 작업 완료 시 알림 전송
    await websocket.send_json({"status": "done", "model_url": "..."})
```

---

## 7. 파일 저장: **로컬 스토리지** 또는 **AWS S3**

| 방식 | 장점 | 단점 |
|------|------|------|
| 로컬 저장 | 간단, 비용 없음 | 확장 어려움 |
| AWS S3 | 확장성, 안정성 | 비용 발생 |

초기 개발 단계에서는 로컬 저장으로 시작하고, 배포 시 S3로 전환 권장

```bash
# S3 사용 시
pip install boto3
```

---

## 8. 환경 설정 관리: **python-dotenv**

```bash
pip install python-dotenv
```

`.env` 파일로 환경변수 관리:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/shoe_db
JWT_SECRET_KEY=your-secret-key
LLM_SERVER_URL=http://llm-server:8000
SPLATTING_SERVER_URL=http://3d-server:8000
REDIS_URL=redis://localhost:6379
```

---

## 9. API 테스트: **pytest** + **httpx**

```bash
pip install pytest pytest-asyncio
```

---

## 📦 전체 requirements.txt

```txt
# Web Framework
fastapi==0.115.*
uvicorn[standard]==0.34.*

# Database
sqlalchemy==2.0.*
asyncpg==0.30.*
alembic==1.14.*

# Authentication
python-jose[cryptography]==3.3.*
passlib[bcrypt]==1.7.*

# HTTP Client (외부 서버 통신)
httpx==0.28.*

# Task Queue
celery==5.4.*
redis==5.2.*

# File Storage (S3 사용 시)
# boto3==1.36.*

# Utilities
python-dotenv==1.0.*
python-multipart==0.0.*

# Testing
pytest==8.3.*
pytest-asyncio==0.25.*
```

---

## 🚀 개발 순서 권장

```
Phase 1 (1~2주차) - 기반 작업
├── FastAPI 프로젝트 셋업
├── PostgreSQL + SQLAlchemy 모델 정의
├── 회원가입/로그인 API (JWT)
└── 기본 CRUD API

Phase 2 (3~4주차) - 핵심 연동
├── LLM 서버 연동 (이미지 생성 요청/수신)
├── Celery + Redis 비동기 작업 큐
├── 생성 상태 조회 API
└── 파일 저장/조회 로직

Phase 3 (5~6주차) - 3D 연동
├── 3D 변환 서버 연동
├── 3D 모델 파일 관리
├── 다운로드 API
└── WebSocket 실시간 알림 (선택)

Phase 4 (7~8주차) - 완성
├── 프론트엔드 연동 테스트
├── 에러 처리 / 로깅
├── 배포 (Docker + 클라우드)
└── 성능 최적화
```

---

## 💡 추가 고려사항

- **CORS 설정**: 프론트엔드와 다른 도메인이면 CORS 미들웨어 필수
- **Rate Limiting**: AI 생성 요청의 남용 방지
- **로깅**: `loguru` 또는 Python 기본 `logging` 활용
- **Docker**: 개발/배포 환경 통일을 위해 Docker Compose 사용 권장
- **API 버전 관리**: `/api/v1/` 형태로 버전 prefix 사용 권장
