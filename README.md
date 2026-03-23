# 👟 Text-to-3D Shoe Platform

> 사용자가 입력한 텍스트를 기반으로 신발 이미지를 생성하고, 가우시안 스플래팅(Gaussian Splatting)을 통해 3D 모델로 변환하여 웹에서 시각화 및 다운로드할 수 있는 플랫폼

---

## 📌 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **목표** | 텍스트 → 신발 이미지 → 3D 모델 생성 → 웹 시각화 & 다운로드 |
| **핵심 기술** | Text-to-Image (LLM), Gaussian Splatting, 3D Viewer |
| **플랫폼** | 웹 기반 (PC/모바일 대응) |

---

## 🔄 전체 파이프라인

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  사용자 입력  │────▶│  Backend (API)   │────▶│  LLM 서버 (AI팀)  │────▶│  Backend (API)  │────▶│  사용자 응답   │
│  (텍스트)    │     │  텍스트 전달      │     │  신발 이미지 생성   │     │  이미지 수신     │     │  이미지 확인   │
└─────────────┘     └──────────────────┘     └───────────────────┘     └─────────────────┘     └──────────────┘
                                                                                                       │
                                                                                                       ▼
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  3D 다운로드  │◀────│  Backend (API)   │◀────│  3D 변환 서버      │◀────│  Backend (API)  │◀────│  3D 변환 요청  │
│  (.ply/.glb) │     │  3D 모델 전달     │     │  Gaussian Splatting│     │  이미지 전달     │     │  사용자 확인   │
└──────────────┘     └──────────────────┘     └───────────────────┘     └─────────────────┘     └──────────────┘
```

---

## 🏗️ 시스템 아키텍처

```
                        ┌──────────────────────────────────┐
                        │           Frontend (Web)          │
                        │  - 텍스트 입력 UI                  │
                        │  - 생성된 이미지 미리보기            │
                        │  - 3D 모델 뷰어 (Three.js)         │
                        │  - 3D 파일 다운로드                 │
                        └──────────────┬───────────────────┘
                                       │ REST API / WebSocket
                        ┌──────────────▼───────────────────┐
                        │      Backend API Server           │
                        │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
                        │  • 사용자 인증/인가 (JWT)           │
                        │  • 텍스트 → LLM 서버 요청 중계      │
                        │  • 이미지 → 3D 변환 서버 요청 중계   │
                        │  • 결과물 저장 및 전달               │
                        │  • 작업 상태 관리 (큐/폴링)          │
                        │  • 파일 스토리지 관리                │
                        └───┬──────────┬───────────┬───────┘
                            │          │           │
              ┌─────────────▼──┐  ┌────▼────────┐  ┌▼─────────────────┐
              │   Database     │  │  LLM 서버   │  │  3D 변환 서버      │
              │  (사용자 정보,  │  │  (AI팀 담당) │  │  (Gaussian        │
              │   생성 이력,   │  │  Text→Image │  │   Splatting)      │
              │   파일 메타)   │  └─────────────┘  └───────────────────┘
              └────────────────┘
```

---

## 👥 역할 분담

| 담당 | 역할 | 주요 산출물 |
|------|------|------------|
| **Backend (나)** | API 서버, DB, 중간 경로 전체 | API 서버, DB 스키마, 파일 관리 |
| **AI/LLM 팀** | 텍스트→신발 이미지 생성 모델 | 이미지 생성 API/모델 |
| **3D 팀** | 가우시안 스플래팅 3D 변환 | 3D 변환 파이프라인 |
| **Frontend 팀** | 웹 UI, 3D 뷰어 | 프론트엔드 애플리케이션 |

---

## 📡 Backend API 엔드포인트 (예시)

### 인증
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/auth/register` | 회원가입 |
| POST | `/api/auth/login` | 로그인 (JWT 발급) |
| GET | `/api/auth/me` | 내 정보 조회 |

### 신발 생성
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/shoes/generate` | 텍스트 기반 이미지 생성 요청 |
| GET | `/api/shoes/:id/status` | 생성 작업 상태 조회 |
| GET | `/api/shoes/:id/image` | 생성된 이미지 조회 |

### 3D 변환
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/shoes/:id/convert-3d` | 3D 모델 변환 요청 |
| GET | `/api/shoes/:id/3d-status` | 3D 변환 상태 조회 |
| GET | `/api/shoes/:id/3d-model` | 3D 모델 파일 조회 |
| GET | `/api/shoes/:id/download` | 3D 파일 다운로드 |

### 이력 관리
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/shoes/history` | 내 생성 이력 조회 |
| DELETE | `/api/shoes/:id` | 생성물 삭제 |

---

## 🗄️ DB 스키마 (초안)

```sql
-- 사용자
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,
    nickname    VARCHAR(100),
    created_at  TIMESTAMP DEFAULT NOW()
);

-- 생성 작업
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

## 📂 프로젝트 폴더 구조 (예상)

```
Backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py             # 환경 설정
│   ├── models/               # DB 모델 (SQLAlchemy)
│   │   ├── user.py
│   │   └── generation.py
│   ├── schemas/              # Pydantic 요청/응답 스키마
│   │   ├── user.py
│   │   └── generation.py
│   ├── routers/              # API 라우터
│   │   ├── auth.py
│   │   ├── shoes.py
│   │   └── download.py
│   ├── services/             # 비즈니스 로직
│   │   ├── auth_service.py
│   │   ├── llm_service.py    # LLM 서버 통신
│   │   ├── 3d_service.py     # 3D 변환 서버 통신
│   │   └── storage_service.py
│   ├── middleware/            # 미들웨어
│   │   └── auth.py
│   └── utils/                # 유틸리티
│       └── file_handler.py
├── storage/                  # 로컬 파일 저장소
│   ├── images/
│   └── models_3d/
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```
