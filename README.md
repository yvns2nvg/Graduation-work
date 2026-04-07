# 🌟 Text-to-3D Full-stack Platform

> 사용자가 텍스트를 입력하면 AI를 통해 2D 이미지를 생성하고, 이를 가우시안 스플래팅(Gaussian Splatting) 기술을 활용하여 3D 모델(.ply, .glb 등)로 변환해 웹상에서 실시간 렌더링 및 다운로드를 제공하는 풀스택 웹 플랫폼입니다.

---

## 📂 프로젝트 구조 (Monorepo)

본 레포지토리는 프론트엔드와 백엔드가 하나의 폴더에서 분리되어 관리되는 모노레포 구조를 가집니다.

- **`Frontend/`** : 사용자 UI, 텍스트 프롬프트 입력, 이미지 결과 확인 및 3D 뷰어(Three.js) 제공 (프론트엔드 담당)
- **`Backend/`** : 클라이언트 통신 API(FastAPI), 사용자 인증, 로컬/외부 LLM 및 3D 변환 서버와의 통신 관리, 데이터베이스 관리 (백엔드 담당)

---

## 🛠️ 기술 스택

### Frontend
- 미정 (React / Next.js / Vue 중 프론트엔드 담당자가 채택 예정)
- Three.js (3D 모델 렌더링 뷰어)

### Backend
- **Framework** : FastAPI (Python)
- **Database** : SQLite (추후 PostgreSQL 등으로 확장 가능) / SQLAlchemy
- **Integration** : WebSockets (실시간 상태 통신), REST API

### AI / Data Pipelines
- 텍스트 → 2D 이미지 생성 (로컬 LLM 혹은 외부 클라우드 GPU 연동)
- 2D 이미지 → 3D 모델 생성 (TRELLIS 아키텍처 기반 Gaussian Splatting 비동기 통신)

---

## 🚀 로컬 개발환경 실행 가이드

백엔드와 프론트엔드를 동시에 띄워서 연동 테스트를 진행하고자 할 때 다음 절차를 따르세요.

### 1. Backend (API 서버) 실행

1. 터미널을 열고 `Backend/` 디렉토리로 이동:
   ```bash
   cd Backend
   ```
2. 가상환경 설정 및 활성화:
   ```bash
   python -m venv venv
   source venv/bin/activate  # (Mac/Linux)
   # venv\Scripts\activate   # (Windows)
   ```
3. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```
4. FastAPI 서버 실행:
   ```bash
   uvicorn app.main:app --reload
   ```
   > ✅ 기본적으로 백엔드는 `http://localhost:8000` 에서 실행됩니다.

### 2. Frontend (웹 클라이언트) 실행

1. 새로운 터미널 창을 열고 `Frontend/` 디렉토리로 이동:
   ```bash
   cd Frontend
   ```
2. 패키지 설치:
   ```bash
   npm install
   # or yarn install
   ```
3. 프론트엔드 서버 실행:
   ```bash
   npm run dev
   # or yarn dev
   ```
   > ✅ 기본적으로 프론트엔드는 `http://localhost:3000` (또는 `5173`)에서 실행됩니다.

---

## 📝 협업 시 주의사항

- **환경 변수 관리 (.env)**: 절대 Git에 커밋하지 않도록 각 폴더의 `.gitignore` 설정을 따르며, 처음 세팅하는 팀원을 위해 템플릿(`.env.example`)만 공유해주세요.
- **CORS 설정 주의**: 로컬 통신을 위해 `Backend/app/main.py`에 프론트엔드의 주소(`http://localhost:3000` 등)가 허용되어(CORS Allow Origins) 있는지 항상 확인해야 합니다.
