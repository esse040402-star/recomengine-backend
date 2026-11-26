# RecomEngine React 프론트엔드

기존 화면 디자인을 유지하고 업로드된 FastAPI 서버에 계정·AI 문항·Steam 정보를 연결한 수정본입니다.
상세 변경 및 DB 전환 준비 사항: `../docs/DB연결_변경내역.md`

## 개발 실행 (Windows PowerShell)

터미널 1: 저장소 루트에서 (처음에는 가짜 DB로 확인하세요)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:USE_MOCK_DB="true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

터미널 2: 저장소 루트에서

```powershell
cd frontend
npm ci
npm run dev
```

브라우저: **http://localhost:5173**
Vite가 `/api`를 `http://127.0.0.1:8000`으로 전달합니다. 프론트에 Supabase 서비스 키나 AI 키를 넣지 마세요. 기존 `.env`를 덮어쓸 필요는 없습니다.

API 없이 화면만 확인하려면 프론트의 `.env.local`에 `VITE_API_ENABLED=false`를 지정하고 Vite를 재시작하세요. 별도 API 서버 주소를 지정해야 할 때만 `.env.example`을 참고합니다.

## 빌드하여 FastAPI에서 함께 보기

```powershell
cd frontend
npm ci
npm run build
cd ..
$env:USE_MOCK_DB="true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**http://127.0.0.1:8000**으로 접속합니다. 이미 서버가 실행 중이었다면 빌드 후 재시작하세요. FastAPI는 `frontend/dist`가 존재할 때만 화면을 제공합니다. React 소스 index.html을 파일 더블클릭으로 실행하지 마세요.

## 검증

```powershell
cd frontend
npm test
npm run build
npm run lint
```

선택적 브라우저 검증은 위의 mock API와 Vite를 켠 뒤 실행합니다.

```powershell
npm install --no-save playwright
npx playwright install chromium
npm run test:browser
```

브라우저 테스트는 임시 테스트 계정을 mock DB에 생성합니다. 실제 DB 서버를 대상으로 실행하지 마세요. 계정 API는 실제 로컬 서버를 사용하고 Steam·AI는 테스트 응답을 사용합니다.

## 현재 동작 방식

- 설문: 빠른 7문항 / 맞춤 28문항 / 플레이 성향 프로필 30문항.
- 계정: 서버 쿠키 세션 복원, 게스트 가입 이관, 자동 저장과 재시도. 미전송 복구본은 설정에서 복구.
- 저장: 현재 서버의 `/api/account/state`에 JSON을 저장합니다. 정규화 테이블 직접 연동은 DB/API 구축 후 진행합니다.
- AI: 28문항 구조를 서버에 보내고 제목 변경을 검증합니다. 기존 선택지·점수는 유지합니다. 실패하면 규칙 기반 설문을 사용합니다.
- Steam: 기존 게임의 상세 정보와 리뷰·뉴스·랭킹을 서버에서 가져옵니다. 실패 시 내장 자료를 유지합니다.
- 개인 평가와 피드백은 개인 계정 자료입니다. 공용 게시나 외부 AI 학습 기능은 아닙니다.
- `docs/frontend-db-reference.json`은 DB 담당자가 참고할 실제 게임/문항 키 자료입니다.
