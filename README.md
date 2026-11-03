# RecomEngine — 팀 프로젝트 공유 저장소

**기존 실행본**과 **개인 테스트 완료 후 팀 검토를 기다리는 새 작업물**을 분리했습니다. 신규 작업물은 승인 전까지 실행 중인 프로젝트에 적용되지 않습니다.

| 경로 | 용도 | 사용 원칙 |
|---|---|---|
| [current-project/](current-project/) | 기존 프로젝트 전체 (React + FastAPI + 데이터 + 테스트) | 팀원 검토 후 검증된 변경만 통합 |
| [submissions/](submissions/) | 새 프론트·백엔드·DB·문서 작업물 공유 | 개인 검증 후 제출하고 팀원 리뷰 |

## 1. 기존 실행본 확인

기존 저장소의 모든 파일과 내부 폴더 구조를 **내용 변경 없이** `current-project/` 아래로 이동했습니다. 저장소를 받은 후 그 위치에서 이전과 동일하게 실행합니다.

### 백엔드 — Windows PowerShell
```powershell
cd current-project
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
$env:USE_MOCK_DB="true"
python -m pytest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
API 문서: http://127.0.0.1:8000/docs

### 프론트엔드 — 별도 PowerShell
```powershell
cd current-project/frontend
npm ci
npm test
npm run build
npm run dev
```
웹 화면: http://localhost:5173

*이미 `current-project` 내부에서 터미널을 연 경우에는 `cd current-project`를 다시 입력하지 않습니다.* 실행법 자세히 보기: [기존 README](current-project/README.md), [프론트 README](current-project/frontend/README.md).

## 2. 새 작업물 제출 → 팀원 검토 → 최신화

1. 각자 PC에서 신규 기능을 구현하고 오류 검사와 실행 테스트를 마칩니다.
2. `submissions/frontend/`, `backend/`, `database/`, `docs/` 중 해당 파트에 **`작성자-작업명/`** 폴더를 생성해 올립니다.
3. 새 작업물과 함께 `README.md`를 작성합니다. 개인 테스트 결과, 현재 실행본에서 대체할 파일 경로, 필요한 의존성 및 알려진 문제를 기록합니다. [제출 양식](submissions/_template/README.md)
4. 다른 팀원이 신규 코드 및 현재 실행본을 비교해 검토합니다.
5. 검토·승인된 작업물만 `current-project/`에 반영합니다. 그 이후 백엔드 테스트, 프론트 테스트·빌드와 실제 화면을 검증하고 PR로 최신화합니다.

예시:
```text
submissions/
  frontend/min-survey-redesign/README.md
  frontend/min-survey-redesign/SurveyPage.jsx
  backend/lee-recommendation-v2/README.md
  backend/lee-recommendation-v2/recommender.py
  database/park-schema-v2/README.md
  database/park-schema-v2/migration.sql
```

**중요:** `submissions/`에 파일을 올리는 것만으로 React 화면이나 FastAPI 서버는 변경되지 않습니다. 실서비스에 연결하려면 해당 코드를 `current-project/`에 통합해야 합니다.

## 3. 오류·보안 방지

- `app/`, `frontend/`, `data/`, `scripts/` 사이의 **기존 상대 위치와 내부 코드**는 유지했습니다. 다만 프로젝트 실행 시 현재 작업 디렉터리는 `current-project/`여야 합니다.
- 과거 저장소 최상위에서 사용하던 `python -m pytest` 및 `cd frontend` 등은 이제 `current-project/`에서 수행합니다.
- 비밀키가 들어 있는 `.env` 및 개인정보는 커밋하지 않습니다. `.env.example`만 공유합니다.
- 실제 Supabase 쓰기 또는 `sql/`의 실행은 DB 담당자 승인 없이 진행하지 않습니다.
- [.github/workflows/verify.yml](.github/workflows/verify.yml)에서 mock DB 기반 Python 테스트와 React 테스트·빌드를 자동 검사합니다.
- 새로운 제출물은 별도 작업 브랜치에서 올리고 PR로 팀원에게 검토받는 것이 좋습니다.
