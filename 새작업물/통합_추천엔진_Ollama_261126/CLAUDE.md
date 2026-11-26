# 게임 추천 백엔드 (RecomEngine) — Claude Code 작업 지침

팀 프로젝트의 **백엔드 담당 부분**입니다. DB(Supabase 스키마)와 프론트(HTML 프로토타입)는 다른 팀원이 만듭니다.
먼저 `README.md`(사용법)와 `HANDOFF.md`(진행 상황)를 읽으세요.

## 절대 규칙 (보안)
- **`.env` 와 `.env.*`(`.env.example` 제외)를 열거나, 출력하거나, 내용을 언급하지 마세요.** API 키·토큰·비밀번호가 들어 있습니다.
- 키 값이 터미널 출력이나 오류 메시지에 보이면 그대로 옮겨 적지 말고 "키가 노출됨"이라고만 알려 주세요.
- 환경변수를 출력하는 명령(`echo $env:...`, `Get-ChildItem Env:`, `printenv`)을 실행하지 마세요.
- 외부 API 오류는 `app/services/safe_errors.py` 의 `describe()`/`status_hint()` 로만 로그/응답에 남기세요 (요청 주소에 `?key=` 가 들어 있음).
- `git commit`, `git push` 는 **제가 확인한 뒤에만** 하세요. 커밋 전에 `git status` 로 `.env`·`.venv` 가 없는지 보여 주세요.
- `sql/` 폴더의 SQL 은 팀원(DB 담당)의 스키마를 바꿉니다. 실행하지 말고 제안만 하세요. `USE_MOCK_DB=false`(실제 DB) 쓰기 작업도 먼저 물어보세요.
- 프론트 프로토타입 HTML(약 32MB)은 저장소에 넣지 마세요. 2026-10-08 수정부터 `frontend/index.html`은 작은 React 진입 파일로 추적합니다. 생성 산출물은 `frontend/dist/`이며 git에 넣지 않습니다. 실행은 `frontend/README.md`를 참고하세요.

## 기술 스택과 구조
FastAPI · Supabase(Auth/DB) · Ollama(로컬 AI, 현재 `qwen2.5:7b`) · RAWG/IGDB(게임 데이터) · 스팀(리뷰/가격/라이브러리)
- `app/main.py` 앱 조립, 오류 형식 `{"error": "한국어 메시지", "detail": ...}` (프론트가 `error` 를 그대로 화면에 표시)
- `app/routers/` account · ai · games · market · sessions · survey · system  (API 25개)
- `app/services/` ai_features(AI 기능 로직) · recommender(추천 점수) · game_clean(RAWG/IGDB 데이터 정리) · games_sync · ollama · rawg · igdb · steam · market(스팀 랭킹·뉴스 조립+캐시) · survey_ai · aliases …
- `data/catalog_apps.json` 프론트 게임 id → 스팀 앱 번호 (프론트 HTML 에서 `python -m scripts.export_catalog` 로 생성)
- `app/docs.py` Swagger 한국어 설명 · `app/static/swagger_ko.js` Swagger 영어 문구 번역
- `app/mock_db.py` 가짜 DB(메모리) · `data/` 샘플 게임, 한국어 별칭표, 설문 문항 · `sql/` 팀원과 합의가 필요한 SQL
- 원칙: **문장 이해·작성은 Ollama, 점수·필터·계산은 코드.** AI 출력은 항상 검증하고, 실패하면 규칙 기반으로 대체합니다.

## 실행과 테스트 (Windows PowerShell, `backend` 폴더에서)
```powershell
.\.venv\Scripts\Activate.ps1
fastapi dev app/main.py                    # http://127.0.0.1:8000/docs
python -m pytest                           # API 통합 테스트 (tests/test_api_*.py)
python -m tests.test_ai_features           # 순수 로직 테스트 (이 외에 test_mock_db, test_prototype_sync,
                                           #   test_docs_coverage, test_search_quality, test_swagger_korean, test_game_clean)
```
- 기본은 `USE_MOCK_DB=true`(가짜 DB, 샘플 게임 19개). 키 없이 개발·테스트할 수 있어야 합니다.
- 새 API 를 만들면 `app/docs.py` 에 한국어 설명을 추가하세요 (`python -m tests.test_docs_coverage` 가 누락을 알려 줌).
- 사용자에게 보이는 메시지·주석·문서는 한국어로 쓰세요.

## 현재 상태 (자세한 내용은 HANDOFF.md)
- 확인함: mock 모드의 진단 흐름, AI 기능, RAWG/IGDB 수집(실제 호출), 계정 API 일부
- 확인함(2026-10-03): `python -m pytest` 75개 통과(mock DB), RAWG·IGDB·스팀(리뷰/가격/라이브러리) 실호출, 실제 Supabase 읽기(`GET /api/games`)
- **아직 못 해본 것**: 실제 Supabase 쓰기·로그인(Auth), 심화 설문 생성 속도(50초 제한)
- 구현함(2026-10-03): 스팀 랭킹·뉴스·할인·리뷰·상세 (`/api/market`, `/api/steam/reviews`, `/api/steam/details`, `feeds` 는 true). 프론트 화면에서 직접 눌러 본 것은 아님
- 미구현: iTunes·구글 플레이·오픈크리틱 연동

## 다음 작업 후보
1. 실제 Supabase 쓰기·로그인 확인 (읽기는 확인함. 쓰기·SQL 적용은 DB 담당과 합의 후)
2. 심화 설문 속도 개선: `app/services/survey_ai.py` 에서 제목만 다시 쓰고 선택지는 원문 유지 (프론트 검증은 선택지 id·개수만 확인)
3. 실제 게임 데이터를 넣은 뒤 추천 유사도 가중치 조정 (`ai_features.py` 의 `GENERIC_TAGS`, 가중치 상수)
4. 문서에 적힌 추가 데이터 소스 연동

## 설명 방식
- 쉬운 한국어로 설명하고, 전문 용어는 처음 나올 때 한 줄로 풀어 쓰세요.
- 파일을 고치거나 명령을 실행하기 전에 "무엇을, 왜" 하는지 한두 문장으로 먼저 알려 주세요.
- 작업이 끝나면 바뀐 파일과 확인 방법(실행할 명령)을 요약하세요.
- 큰 변경은 먼저 계획을 보여 주고 제가 동의한 뒤에 진행하세요.
