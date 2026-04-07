# 🖥️ Text-to-3D Generation Backend

> 사용자가 입력한 텍스트를 기반으로 이미지를 생성하고, 가우시안 스플래팅(Gaussian Splatting)을 통해 3D 모델로 변환하여 웹에서 시각화 및 다운로드할 수 있는 플랫폼의 백엔드 시스템입니다.

---

## 📌 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **핵심 기능** | 텍스트 → 이미지 생성 → 3D 모델 생성 (파이프라인 관리 및 상태 조회) |
| **핵심 기술** | FastAPI, Text-to-Image (로컬/외부 LLM 연동), Gaussian Splatting (TRELLIS 연동), WebSocket |
| **데이터 유지** | SQLite / SQLAlchemy / 로컬 파일 스토리지 |

---

## 🔄 전체 파이프라인

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  사용자 입력   │────▶│  Backend (API)   │────▶│  LLM 서버 (AI팀)   │────▶│  Backend (API)  │────▶│  사용자 응답    │
│  (텍스트)     │     │  텍스트 전달        │     │  이미지 생성       │     │  이미지 수신       │     │  이미지 확인    │
└─────────────┘     └──────────────────┘     └───────────────────┘     └─────────────────┘     └──────────────┘
                                                                                                       │
                                                                                                       ▼
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  3D 다운로드   │◀────│  Backend (API)   │◀────│  3D 변환 서버        │◀────│  Backend (API)  │◀────│  3D 변환 요청  │
│  (.ply/.glb) │     │  3D 모델 전달      │     │  Gaussian Splatting│     │  이미지 전달       │     │  사용자 확인   │
└──────────────┘     └──────────────────┘     └───────────────────┘     └─────────────────┘     └──────────────┘
```

---

## 🏗️ 백엔드 시스템 아키텍처

```
                        ┌──────────────────────────────────┐
                        │           Frontend (Web)         │
                        │  - 텍스트 입력 UI                   │
                        │  - 생성된 이미지 미리보기              │
                        │  - 3D 모델 뷰어 (Three.js)         │
                        │  - 3D 파일 다운로드                 │
                        └──────────────┬───────────────────┘
                                       │ REST API / WebSocket
                        ┌──────────────▼───────────────────┐
                        │      Backend API Server          │
                        │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
                        │  • 사용자 인증/인가 (JWT)            │
                        │  • 텍스트 → LLM 서버 요청 중계        │
                        │  • 이미지 → 3D 변환 서버 요청 중계     │
                        │  • 결과물 저장 및 전달               │
                        │  • 작업 상태 관리 (웹소켓/폴링)       │
                        │  • 파일 스토리지 관리                │
                        └───┬──────────┬───────────┬───────┘
                            │          │           │
              ┌─────────────▼──┐  ┌────▼────────┐  ┌▼─────────────────┐
              │   Database     │  │  LLM 서버   │  │  3D 변환 서버      │
              │  (사용자 정보,  │  │  (AI팀 담당) │  │  (TRELLIS -       │
              │   생성 이력,   │  │  로컬 모델   │  │   Gaussian        │
              │   파일 메타)   │  │  Linux Cloud│  │   Splatting)      │
              │               │  │  GPU 서버   │  │  Linux Cloud      │
              │               │  │  호환 규격   │  │  GPU 서버          │
              └────────────────┘  └─────────────┘  └───────────────────┘
```

---

## 📡 Backend API 엔드포인트 주요 흐름

### 1. 인증 (Auth)
- `POST /api/auth/register` : 회원가입
- `POST /api/auth/login` : 로그인 (JWT)
- `GET /api/auth/me` : 내 정보 조회

### 2. 생성 파이프라인 (Text-to-3D)
- `POST /api/text-to-3d/generate` : 텍스트 기반 이미지 생성 요청
- `GET /api/text-to-3d/:id/status` : 생성 작업 상태 조회
- `GET /api/text-to-3d/:id/image` : 결과 이미지 조회
- `POST /api/text-to-3d/:id/convert-3d` : 3D 모델 변환 요청
- `GET /api/text-to-3d/:id/3d-status` : 3D 변환 상태 조회
- `GET /api/text-to-3d/:id/3d-model` : 3D 모델 파일 조회

### 3. 다운로드 및 실시간 소켓 (Download & WebSocket)
- `GET /api/download/:id` : 3D 파일 다운로드
- `WS /ws/generation/:id` : 생성 상태 실시간 스트리밍 소켓 연결

---

## 🗄️ DB 스키마 요약

```sql
-- 사용자
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,
    nickname    VARCHAR(100),
    created_at  TIMESTAMP DEFAULT NOW()
);

-- 생성 작업 데이터
CREATE TABLE generations (
    id              SERIAL PRIMARY KEY,
    user_id         INT REFERENCES users(id),
    prompt_text     TEXT NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',  -- pending / generating / image_done / converting / done / failed
    image_url       VARCHAR(500),
    model_3d_url    VARCHAR(500),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 📂 Backend 프로젝트 구조 정리

```
Backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py             # 환경 설정
│   ├── models/               # DB 모델 (SQLAlchemy)
│   ├── schemas/              # Pydantic 요청/응답 스키마
│   ├── routers/              # API 라우터 (auth.py, text_to_3d.py, download.py, websocket.py)
│   ├── services/             # 비즈니스 로직 (Auth, LLM 통신, TRELLIS 연동 설계, Storage)
│   ├── middleware/            # 로깅, 인증 미들웨어
│   └── utils/                # 유틸 모듈
├── storage/                  # 로컬 파일 저장소 (이미지, 3D 에셋 보관)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
