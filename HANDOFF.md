# 백엔드 진행 상황 (팀 공유용)

> 작성 기준: 2026-10-02. 자세한 사용법은 `README.md`, API 목록은 서버를 켠 뒤 http://127.0.0.1:8000/docs (한국어 설명 포함).

## 한 줄 요약
FastAPI 백엔드 골격과 AI(Ollama) 기능, RAWG/IGDB 게임 수집, 회원/로그인 API까지 **가짜 DB(mock) 모드에서 동작을 확인**했습니다.
실제 Supabase는 읽기만 확인했고, 쓰기·로그인과 프론트 연결은 아직 안 했습니다 (담당자와 맞춘 뒤 진행).

## 지금 되는 것 (mock 모드, /docs 에서 직접 확인함)
- 취향 진단 흐름: 세션 시작 → 답변 저장 → 완료(6축 점수·리포트·추천 10개 저장) → 결과 조회
- AI 기능(Ollama): 자연어 검색·대체제, 비슷한 게임, 추천 이유, 백로그 처리반, 플레이타임 계산기, 리뷰 요약, 할인/출시예정 정렬
  - Ollama가 꺼져 있어도 대부분 규칙 기반으로 대체 동작 (`source: "rule"`)
- 게임 데이터 수집: RAWG(+IGDB 보강) → 장르 통일·기능 태그 제거·비공식 항목 제외 후 저장 (RAWG 실제 호출 확인함)
- 계정: 회원가입/로그인/로그아웃/화면 상태 저장 (쿠키 로그인), 오류는 `{"error": "한국어 메시지"}` 형식
- 자동 테스트: `python -m pytest` 89개 전부 통과 (2026-10-03, `USE_MOCK_DB=true` 로 실행)
- 스팀 랭킹·뉴스·할인·리뷰·상세 API: 가짜 응답 테스트 + 실제 스팀 읽기 전용 호출로 확인 (2026-10-03)
- 외부 API 실호출 확인 (2026-10-03): RAWG·IGDB 검색, 스팀 리뷰·가격·내 라이브러리(API 키 포함) 모두 정상

## 아직 안 된 것 / 확인하지 못한 것
- **실제 Supabase 연결은 읽기만 확인** (2026-10-03, `GET /api/games` 정상). 쓰기·로그인(Auth)은 `USE_MOCK_DB=false` 로 돌려본 적 없음
- 스팀 랭킹/뉴스 API 는 만들었지만 **프론트 화면에서 실제로 눌러 본 적은 없음** (아래 '프론트 담당자에게' 참고)
- iTunes·구글 플레이·오픈크리틱 등 문서에 적힌 다른 데이터 소스 미연동
- 추천 품질은 샘플 게임 19개 기준으로만 확인. 실제 게임 데이터를 넣은 뒤 가중치 조정 필요
- Ollama 심화 설문 생성이 50초 제한을 넘기면 프론트가 기본 문항으로 대체함 (모델/PC 성능에 따라)

## DB 담당자에게 (합의 필요)
백엔드는 서비스 키로 DB에 접속합니다 (`SUPABASE_SERVICE_KEY`, 서버 전용 · 프론트에 주지 말 것).

**1) `sql/001_constraints.sql` — 기존 스키마를 바꿉니다. 실행 전에 꼭 확인해 주세요**
- `diagnosis_answers.question_id` 의 외래키 제거: 프론트 질문 id(`q1`, `d01` …)와 `survey_questions.id`(`G_ONB_01` …) 형식이 달라서
- `diagnosis_answers (session_id, question_id)` 유니크 인덱스: 답변 덮어쓰기(upsert)에 필요
- `recommendations (session_id, game_id)` 유니크 인덱스
- 7개 테이블 RLS 활성화 (정책 없음 → 서비스 키만 접근)

**2) `sql/002_user_states.sql` — 새 테이블 1개 추가** (`user_states`: 로그인한 사용자의 화면 상태 저장)

**3) 백엔드가 쓰는 테이블**
- 쓰기: `diagnosis_sessions`, `diagnosis_answers`, `analysis_scores`, `analysis_reports`, `recommendations`, `games`(RAWG/IGDB 동기화, `rawg_id`/`igdb_id` 기준 upsert, `steam_app_id`·`price_info` 포함), `user_states`
- 읽기: 위 테이블 전부 + `games` 전체(1000행씩 나눠 읽음)
- 로그인: Supabase Auth 사용 (가입 시 이메일 인증 없이 바로 활성화). 로그인 검증에 `SUPABASE_ANON_KEY` 필요
- 설문 문항 60개 시드: `python -m scripts.seed_survey_questions` (`survey_questions` 에 upsert)

## 프론트 담당자에게
1. **요청 한 줄 추가 필요**: `/api/survey/generate` 호출 2곳의 body 에 `blueprint:E.publicBlueprint(트랙,답변)` 추가. 직접 고치기 싫으면 `python -m scripts.patch_frontend "<html 경로>"` 로 자동 패치
2. 오류 응답은 `{"error": "화면에 보여줄 한국어 메시지", "detail": ...}` 입니다
3. **로그인은 쿠키 방식**이라 프론트 HTML 을 백엔드와 **같은 주소**(`backend/frontend/index.html` → http://localhost:8000)로 열어야 동작합니다
4. 계정 API: `GET /api/account/session`, `POST /signup|/login|/logout`, `PUT /state` (규격은 README 표 참고)
5. 코드와 카탈로그 데이터를 읽어서 확인한 문제 (화면에서 실행해 본 것은 아님, 확인 필요)
   - 비게이머 Q1 "일반 사무용 컴퓨터/노트북" → `lowSpec` 을 요구하는데 카탈로그에 `lowSpec: true` 게임이 0개
   - 불호 "P2W/과금 피로" → `riskCoverage` 에 `monetization` 이 있어야 통과하는데 0개
   - 둘 다 `recommend()` 가 빈 결과를 낼 수 있음
6. **스팀 랭킹/뉴스 API 구현 완료** (2026-10-03): 프론트가 부르는 `/api/market?section=rankings|news|reviews`, `/api/steam/reviews`, `/api/steam/details` 를 프로토타입 HTML 의 호출 코드에 맞춰 만들었고 `/api/status` 의 `feeds` 가 `true` 입니다
   - 프론트는 게임을 자기 id(`elden`)로 부르므로 `data/catalog_apps.json`(id → 스팀 앱 번호)이 필요합니다. 게임 목록이 바뀌면 `python -m scripts.export_catalog "<html 경로>"` 로 다시 만드세요
   - 게임 지정 없는 전체 뉴스는 대표 게임 12개만 조회하고, 결과는 서버 메모리에 10~30분 보관합니다 (DB 저장 없음)
   - 인기 순위의 접속자 수(`players`)를 못 가져온 줄은 `null` 로 오고, 화면에는 '집계 대기'로 보입니다

## 실행 요약
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
copy .env.example .env     # .env 에 본인 키 입력 (USE_MOCK_DB=true 면 키 없이 시험 가능)
fastapi dev app/main.py    # http://127.0.0.1:8000/docs
```

## 키 / 보안 규칙
- `.env` 는 절대 공유·업로드하지 않습니다 (압축 파일에는 `.env.example` 만 들어 있음)
- Supabase **service/secret 키** 는 서버 전용입니다. 필요한 사람에게만 개인 메시지로 전달하고, 단체방·깃허브·스크린샷에 올리지 않습니다
- `SESSION_SECRET`, `ADMIN_TOKEN` 은 사람마다 각자 새로 만듭니다 (README 참고)
