# 백엔드 진행 상황 (팀 공유용)

> 작성 기준: 2026-10-02 · **2026-10-09 React 프론트(GitHub `c0b2272`) 연동 기준으로 갱신**. 자세한 사용법은 `README.md`, API 목록은 서버를 켠 뒤 http://127.0.0.1:8000/docs (한국어 설명 포함).

## 한 줄 요약
FastAPI 백엔드 골격과 AI(Ollama) 기능, RAWG/IGDB 게임 수집, 회원/로그인 API를 **가짜 DB(mock) 모드에서 React 프론트와 함께 화면까지 확인**했습니다 (2026-10-09).
실제 Supabase는 읽기만 확인했고, 쓰기·로그인(Auth)은 아직 안 했습니다 (담당자와 맞춘 뒤 진행).

## 지금 되는 것 (mock 모드, /docs 에서 직접 확인함)
- 취향 진단 흐름: 세션 시작 → 답변 저장 → 완료(6축 점수·리포트·추천 10개 저장) → 결과 조회
- AI 기능(Ollama): 자연어 검색·대체제, 비슷한 게임, 추천 이유, 백로그 처리반, 플레이타임 계산기, 리뷰 요약, 할인/출시예정 정렬
  - Ollama가 꺼져 있어도 대부분 규칙 기반으로 대체 동작 (`source: "rule"`)
- 게임 데이터 수집: RAWG(+IGDB 보강) → 장르 통일·기능 태그 제거·비공식 항목 제외 후 저장 (RAWG 실제 호출 확인함)
- 계정: 회원가입/로그인/로그아웃/화면 상태 저장 (쿠키 로그인), 오류는 `{"error": "한국어 메시지"}` 형식
- 자동 테스트: `python -m pytest` 90개 전부 통과 (2026-10-09, `USE_MOCK_DB=true` 로 실행). 프론트 `npm test` 8개 통과, `npm run build` 성공
- **React 프론트 화면 연동 확인 (2026-10-09, 가짜 DB, http://127.0.0.1:8000)**: 7문항 설문 → 결과 5개, 회원가입(게스트 찜·설문 이관) → 새로고침 후 로그인·상태 유지, 스팀 뉴스 새로 불러오기, 리뷰 필터 조회(12개·다음 페이지), 상세 갱신, AI 맞춤 설문 28문항 생성(약 15~22초, 화면에 "AI가 생성한 질문입니다")
- 스팀 랭킹·뉴스·할인·리뷰·상세 API: 가짜 응답 테스트 + 실제 스팀 읽기 전용 호출로 확인 (2026-10-03)
- 스팀 **인기 순위**: 2026-10-09 새벽 한동안 스팀의 `ISteamChartsService` 주소가 500(`Transport error`)을 내서 우리 서버도 502 였지만(서버 코드 문제 아님), 같은 날 복구되어 화면에서 `새로 불러오기`로 실시간 순위(확인 시각 갱신)를 확인했습니다. 스팀이 다시 오류를 내면 서버는 502, 화면은 저장된 자료를 유지하고 안내 토스트를 보여 줍니다
- 외부 API 실호출 확인 (2026-10-03): RAWG·IGDB 검색, 스팀 리뷰·가격·내 라이브러리(API 키 포함) 모두 정상

## 아직 안 된 것 / 확인하지 못한 것
- **실제 Supabase 연결은 읽기만 확인** (2026-10-03, `GET /api/games` 정상). 쓰기·로그인(Auth)은 `USE_MOCK_DB=false` 로 돌려본 적 없음
- iTunes·구글 플레이·오픈크리틱 등 문서에 적힌 다른 데이터 소스 미연동
- 추천 품질은 샘플 게임 19개 기준으로만 확인. 실제 게임 데이터를 넣은 뒤 가중치 조정 필요
- Ollama 심화 설문 생성이 50초 제한을 넘기면 프론트가 기본 문항으로 대체함 (모델/PC 성능에 따라). 2026-10-09 측정에서는 15~22초였습니다 (qwen2.5:7b, 이 PC 기준)
- AI 가 바꾼 설문 제목이 다른 문항의 원래 제목과 겹쳐서 프론트가 응답 전체를 버리던 문제를 2026-10-09 에 고쳤습니다 (`survey_ai.sanitize`). 재현 테스트는 `tests/test_prototype_sync.py`

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
> React 프론트(`frontend/`)는 서버 경로에 이미 맞춰져 있어 서버 쪽 추가 요청은 없습니다. 확인·수정 요청은 **`docs/프론트엔드_수정_요청서_20261009.md`** 에 정리했습니다.

1. 오류 응답은 `{"error": "화면에 보여줄 한국어 메시지", "detail": ...}` 입니다 (프론트 `transport.js` 가 `error`·`message` 둘 다 읽음)
2. **로그인은 쿠키 방식**이라 서버와 **같은 주소**(`frontend` 를 빌드해 http://localhost:8000, 또는 Vite 프록시를 쓰는 http://localhost:5173)로 열어야 동작합니다. 실행 방법은 README '6단계'
3. 계정 API: `GET /api/account/session`, `POST /signup|/login|/logout`, `PUT /state` (규격은 README 표 참고)
4. 화면을 실제로 눌러 확인한 문제 (코드·카탈로그 데이터 기준, 요청서에 상세)
   - **추천 0건**: 저사양(`lowSpec` 0개)·과금 피로(`monetization` 확인 0개) 외에도 `pvp`·`mature` 이외의 제외 요소를 하나만 골라도 Steam 파생 121개가 모두 빠져 큐레이션 15개만 남음 (높은 난이도 7개, 복잡한 규칙 9개 등)
   - "이 브라우저에만 저장" 문구가 로그인 후에도 남아 있음 (스토리보드에도 있는 문구라 기획 확인 필요)
5. **스팀 랭킹/뉴스 API 구현 완료** (2026-10-03, 2026-10-09 화면 확인): 프론트가 부르는 `/api/market?section=rankings|news|reviews`, `/api/steam/reviews`, `/api/steam/details` 가 있고 `/api/status` 의 `feeds` 가 `true` 입니다. 이미지(`steamMediaURL`)는 프론트가 스팀 주소를 직접 불러서 서버 중계 API 는 없습니다
   - 프론트는 게임을 자기 id(`elden`)로 부르므로 `data/catalog_apps.json`(id → 스팀 앱 번호)이 필요합니다. 게임 목록이 바뀌면 `python -m scripts.export_catalog` 로 다시 만드세요 (프론트 `src/data/generated/` 를 읽음)
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
