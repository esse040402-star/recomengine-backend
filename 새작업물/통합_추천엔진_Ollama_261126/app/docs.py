"""Swagger(/docs) 화면에 보이는 한국어 설명을 한곳에 모아둔 파일.
설명을 고치고 싶으면 이 파일만 수정하면 됩니다. 라우터는 `@router.get("/경로", **doc("키"))` 형태로 가져다 씁니다."""

# ---------------------------------------------------------------- 태그(그룹 제목)
SYSTEM = "system (서버 상태)"
ACCOUNT = "account (회원·로그인)"
SESSIONS = "sessions (취향 진단)"
SURVEY = "survey (설문 문항 AI)"
GAMES = "games (게임 목록)"
AI = "ai (AI 검색·추천)"
MARKET = "market (스팀 랭킹·뉴스)"

OPENAPI_TAGS = [
    {"name": SYSTEM, "description": "서버와 AI(Ollama)가 정상인지 확인합니다."},
    {"name": ACCOUNT, "description": "회원가입, 로그인, 로그아웃, 내 화면 상태 저장. 로그인 상태는 쿠키로 유지됩니다."},
    {"name": SESSIONS, "description": "취향 진단 한 번 = 세션 하나. **시작 → 답변 저장 → 완료(점수·리포트·추천 생성) → 결과 조회** 순서로 사용합니다."},
    {"name": SURVEY, "description": "기존 설문 문항을 조회하고 문장 생성 기능을 제공합니다. 신규 맞춤 추천은 자유 대화형 AI로 진행합니다."},
    {"name": GAMES, "description": "DB에 저장된 게임 목록·상세 조회, 그리고 RAWG/IGDB에서 게임 데이터를 가져오는 관리자 기능."},
    {"name": AI, "description": '자연어 게임 검색과 자유 대화형 게임 추천을 제공합니다. 문장 이해와 작성은 Ollama가 하고 점수와 필터는 코드가 계산합니다. 자유 대화형 추천은 Ollama 연결이 필요합니다.'},
    {"name": MARKET, "description": "스팀 인기 순위, 게임 소식·신작·할인, 리뷰, 상세 정보를 실시간으로 가져옵니다. 키가 필요 없는 스팀 공개 주소를 쓰고, "
                                    "스팀을 자주 부르지 않도록 서버가 몇 분~1시간 동안 결과를 보관합니다. DB에는 저장하지 않습니다."},
]

APP_DESCRIPTION = """
게임 추천 사이트(RecomEngine)의 백엔드 API입니다. **각 항목을 눌러 펼친 뒤 `Try it out` → `Execute`** 로 직접 호출해 볼 수 있어요.

### 처음 써보는 순서
1. `GET /api/status` 로 서버 상태 확인 (`mock_db: true` 면 가짜 DB로 동작 중)
2. `POST /api/sessions` 로 진단 시작 → 응답의 `id` 복사
3. `PUT /api/sessions/{session_id}/answers` 로 답변 저장
4. `POST /api/sessions/{session_id}/complete` 로 점수·리포트·추천 생성
5. `GET /api/sessions/{session_id}/result` 로 결과 확인

### 알아두기
- 실패 응답은 항상 `{"error": "한국어 메시지", "detail": ...}` 형태입니다.
- **mock 모드**(`.env` 의 `USE_MOCK_DB=true`)에서는 서버를 끄면 저장한 데이터가 사라집니다.
- 관리자 API(`admin`)는 `X-Admin-Token` 헤더(= `.env` 의 `ADMIN_TOKEN`)가 필요합니다.
- 로그인한 것처럼 테스트하려면 `Authorization: Bearer mock-이름` 헤더를 넣으세요 (mock 모드 전용).
"""

# ---------------------------------------------------------------- 공통 오류 설명
ERRORS = {
    401: "로그인이 필요하거나 토큰이 올바르지 않음",
    403: "접근 권한이 없음 (다른 사람의 세션, 관리자 토큰 오류 등)",
    404: "대상을 찾을 수 없음",
    409: "지금 상태에서는 처리할 수 없음",
    413: "보낸 데이터가 너무 큼",
    422: "입력값이 올바르지 않음 (필수 값 누락, 형식 오류 등)",
    429: "시도 횟수 초과 (잠시 후 다시 시도)",
    502: "외부 서비스(스팀·AI)의 응답이 올바르지 않음",
    503: "AI·외부 서버에 연결할 수 없음",
}


def spec(summary: str, description: str, ok=None, ok_code: int = 200, ok_text: str = "성공", errors=()) -> dict:
    responses: dict = {ok_code: {"description": ok_text}}
    if ok is not None:
        responses[ok_code]["content"] = {"application/json": {"example": ok}}
    for code in errors:
        responses[code] = {
            "description": ERRORS[code],
            "content": {"application/json": {"example": {"error": "화면에 보여줄 한국어 오류 메시지"}}},
        }
    return {"summary": summary, "description": description.strip(), "responses": responses}


def doc(key: str) -> dict:
    return dict(DOCS[key])


# ---------------------------------------------------------------- 예시 데이터
UID = "3f2b8c1e-0000-4000-8000-000000000001"
GID = "9a7d5e42-0000-4000-8000-0000000000aa"
GAME_BRIEF = {"id": GID, "title": "Elden Ring", "cover_url": None, "genres": ["Action", "RPG"],
              "platforms": ["PC", "PlayStation 5"], "release_date": "2022-02-25"}
RESULT_EXAMPLE = {
    "session": {"id": UID, "track": "gamer", "status": "completed", "user_id": None,
                "started_at": "2026-10-02T08:30:00+00:00", "completed_at": "2026-10-02T08:35:00+00:00"},
    "scores": {"session_id": UID, "physical": 90, "strategy": 50, "exploration": 60, "emotion": 60,
               "comfort": 15, "competition": 70, "platform_fit": {"selected": ["pc"]}},
    "report": {"session_id": UID, "profile_name": "손맛을 즐기는 도전자", "keywords": ["조작·피지컬", "경쟁·성취"],
               "summary": {"headline": "조작·피지컬과 경쟁·성취에서 즐거움을 찾는 타입", "text": "…"},
               "detail": {"strengths": ["…"], "style": "…"}, "anti_match": {"avoid": ["…"], "reason": "…"},
               "play_tip": {"tips": ["…"]}, "generated_by": "ollama", "model_name": "qwen2.5:7b"},
    "recommendations": [{"rank": 1, "match_score": 84.0, "reason": "조작·피지컬 · 경쟁·성취 성향과 Souls-like, Difficult 요소가 잘 맞아요.",
                         "matched_tags": ["Souls-like", "Difficult"], "algorithm_version": "axis-tag-v1", "games": GAME_BRIEF}],
}
AI_RESULT_ITEM = {"game": {**GAME_BRIEF, "tags": ["Cozy"], "playtime_hours": 50, "price_info": {}}, "score": 45.0,
                  "matched": ["Simulation", "Cozy"], "reason": "편하게 쉬고 싶은 분께 [Stardew Valley]를 추천해요.",
                  "reason_source": "ollama"}

# ---------------------------------------------------------------- 엔드포인트별 설명
DOCS: dict[str, dict] = {
    # ---------------- system
    "status": spec(
        "Status (서버·AI 연결 상태 확인)",
        """
서버가 살아있는지, Ollama(AI)가 켜져 있는지 확인합니다. 프론트 화면은 열릴 때 이 API를 한 번 호출합니다.

**응답 필드**
- `ai` : Ollama가 켜져 있고 `.env`에 적은 모델이 설치되어 있으면 `true` (프론트가 AI 설문 생성을 시도할지 정하는 값)
- `feeds` : 스팀 랭킹·뉴스·리뷰 실시간 조회(`/api/market`, `/api/steam/*`) 사용 여부 (키가 필요 없어 항상 `true`). 프론트는 이 값이 `true` 일 때 '새로 불러오기' 버튼을 보여줍니다
- `ollama` : `up`(Ollama 실행 중인지), `model`(`.env`에 설정한 모델), `model_ready`(그 모델이 설치됐는지)
- `rawg` / `igdb` / `steam` : 해당 API 키가 `.env`에 들어 있는지
- `mock_db` : `true` 면 Supabase 대신 **메모리 가짜 DB**로 동작 중 (서버를 끄면 데이터 삭제)
        """,
        {"ai": False, "feeds": True, "ollama": {"up": False, "model": "qwen2.5:7b", "model_ready": False},
         "rawg": False, "igdb": False, "steam": False, "mock_db": True},
        ok_text="현재 서버 상태",
    ),
    # ---------------- account
    "account_session": spec(
        "Get Session (현재 로그인 상태 확인)",
        """
쿠키를 보고 지금 로그인되어 있는지 알려줍니다. 프론트는 페이지를 열 때 호출합니다.
- 로그인 안 됨: `{"user": null}`
- 로그인 됨: `user`(id, 닉네임, 이메일)와, 이전에 저장해 둔 화면 상태가 있으면 `state` 도 함께 돌려줍니다.
  (이메일 기능 추가 전에 발급된 쿠키면 `email` 은 빈 글자입니다. 다시 로그인하면 채워집니다)
        """,
        {"user": {"id": UID, "name": "지헌", "email": "user@example.com"}, "state": {"track": "gamer", "quick": {"completed": True}}},
        ok_text="로그인 상태 (로그인 안 됐으면 user 가 null)",
    ),
    "account_signup": spec(
        "Signup (회원가입)",
        """
닉네임·이메일·비밀번호(8자 이상)로 가입합니다. Supabase Auth의 이메일 인증 설정에 따라 바로 로그인되거나 인증 메일 확인이 필요합니다. Mock DB에서는 실제 메일을 보내지 않고 시연용 인증 단계를 거칩니다.
비밀번호는 Supabase Auth가 해시 처리해 보관하며 이 서버는 저장하지 않습니다.
이미 가입된 이메일이면 409를 돌려줍니다. `guest_session_ids` 에 완료된 비회원 진단 세션 ID를 보내면 인증 성공 후 계정에 연결합니다(최대 20개).
- **같은 IP에서 10분 동안 10번 넘게 시도하면 429** 로 막습니다 (가짜 계정 대량 생성 방지)
        """,
        {"user": {"id": UID, "name": "지헌", "email": "user@example.com"}, "guest_sessions_claimed": 1, "guest_session_claim_failed": False}, ok_code=201, ok_text="가입 완료", errors=(409, 422, 429, 502),
    ),
    "account_mock_email_verify": spec(
        "Mock Email Verify (시연용 이메일 인증)",
        """
USE_MOCK_DB=true인 로컬 시연 환경에서만 사용하는 테스트 인증입니다. 회원가입 응답의 mock_verification_token을 보내면 계정의 이메일 인증 상태를 완료로 변경합니다. 실제 이메일은 발송하지 않으며 실제 Supabase 인증에는 영향을 주지 않습니다.
        """,
        {"verified": True}, ok_text="시연용 이메일 인증 완료", errors=(400, 404, 422),
    ),
    "account_login": spec(
        "Login (로그인)",
        """
이메일·비밀번호로 로그인합니다. 성공하면 쿠키가 발급되고, 이전에 저장해 둔 화면 상태가 있으면 `state` 로 함께 돌려줍니다. `guest_session_ids` 에 완료된 비회원 진단 세션 ID를 보내면 해당 계정으로 연결합니다(최대 20개).
- 이메일 또는 비밀번호가 틀리면 401 (어느 쪽이 틀렸는지는 알려주지 않습니다)
- **8번 연속 실패하면 15분 동안 429** 로 막습니다 (올바른 비밀번호도 거부)
        """,
        {"user": {"id": UID, "name": "지헌", "email": "user@example.com"}, "state": {"track": "gamer"}, "guest_sessions_claimed": 1, "guest_session_claim_failed": False}, ok_text="로그인 성공", errors=(401, 422, 429, 502, 503),
    ),
    "account_logout": spec(
        "Logout (로그아웃)", "로그인 쿠키를 지웁니다. 로그인 상태가 아니어도 성공으로 처리합니다.", {"ok": True}, ok_text="로그아웃 완료",
    ),
    "account_state": spec(
        "Save State (내 화면 상태 저장)",
        """
로그인한 사용자의 화면 상태(설문 답변, 찜한 게임 등)를 통째로 저장합니다. 프론트가 변경이 있을 때마다 자동으로 호출합니다.
**로그인이 필요**하고, 데이터는 1MB 이하여야 합니다. 같은 사용자가 다시 저장하면 이전 내용을 덮어씁니다.
        """,
        {"ok": True}, ok_text="저장 완료", errors=(401, 413, 422, 503),
    ),
    # ---------------- sessions
    "sessions_create": spec(
        "Create Session (취향 진단 시작)",
        """
취향 진단을 새로 시작하고 **세션 id** 를 돌려줍니다. 이후 API들은 이 id 를 사용합니다.
- `track` : `gamer`(게임을 즐기는 사람) 또는 `nongamer`(게임이 낯선 사람)
- 로그인 상태면 내 계정에 연결되고(나만 볼 수 있음), 아니면 비회원 세션이 됩니다.
        """,
        {"id": UID, "track": "gamer", "user_id": None, "status": "in_progress",
         "started_at": "2026-10-02T08:30:00+00:00", "completed_at": None},
        ok_code=201, ok_text="세션 생성됨 (id 를 복사해 두세요)", errors=(401, 422),
    ),
    "sessions_answers": spec(
        "Save Answers (답변 저장)",
        """
설문 답변을 저장합니다. 여러 개를 한 번에 보낼 수 있고, **같은 질문에 다시 보내면 덮어씁니다.**
- `question_id` : 프론트의 질문 id (예: `q1`, `d01`)
- `answer` : 선택한 선택지 id 목록 등 (JSON이면 무엇이든 가능, `null` 은 불가)
- 이미 완료된 세션에는 저장할 수 없습니다(409).
        """,
        {"saved": 1}, ok_text="저장한 답변 개수", errors=(401, 403, 404, 409, 422),
    ),
    "sessions_complete": spec(
        "Complete Session (진단 완료 → 점수·리포트·추천 생성)",
        """
진단을 마무리하면서 **점수 저장 → 취향 리포트 생성 → 게임 10개 추천 → 세션 완료 처리**를 한 번에 합니다.
- `axes` : 6개 성향 점수(0~100). **순서는 [조작·피지컬, 전략·문제 해결, 탐색·수집, 감성·몰입, 휴식·힐링, 경쟁·성취]**
- `prefs` : 사용자가 고른 조건. `platforms`(pc/console/umpc; 모바일 전용 게임은 추천 제외), `avoid`(motion/grind/text/pvp/complex/horror/difficulty/mature/flash/pressure/monetization…), `lowSpec`(저사양 선호)
- 리포트는 **Ollama가 켜져 있으면 AI가 작성**하고, 꺼져 있으면 규칙 기반으로 만듭니다. 응답 `report.generated_by` 가 `ollama` / `rule` 로 알려줍니다.
- 같은 세션에 다시 호출하면 결과를 새로 계산해서 덮어씁니다.
        """,
        RESULT_EXAMPLE, ok_text="저장된 진단 결과 전체", errors=(401, 403, 404, 422),
    ),
    "sessions_result": spec(
        "Get Result (진단 결과 조회)",
        """
완료된 진단의 결과를 다시 불러옵니다.
- `scores` : 6개 성향 점수 / `report` : 취향 리포트 / `recommendations` : 추천 게임(순위 순)
- 아직 완료하지 않은 세션이면 `scores`, `report` 가 `null`, `recommendations` 는 빈 목록입니다.
        """,
        RESULT_EXAMPLE, ok_text="저장된 진단 결과", errors=(401, 403, 404, 422),
    ),
    # ---------------- games
    "games_list": spec(
        "List Games (게임 목록·검색)",
        """
DB에 저장된 게임을 제목·장르로 찾아 목록으로 돌려줍니다. 페이지는 `limit`(한 번에 개수)과 `offset`(건너뛸 개수)으로 넘깁니다.
응답의 `total` 은 조건에 맞는 전체 개수입니다.
        """,
        {"items": [GAME_BRIEF], "total": 1, "limit": 24, "offset": 0}, ok_text="게임 목록", errors=(422,),
    ),
    "games_detail": spec(
        "Get Game (게임 상세)",
        "게임 하나의 모든 정보(설명, 태그, 플랫폼, 플레이타임, 가격 정보 등)를 돌려줍니다. `game_id` 는 목록 API 응답의 `id` 입니다.",
        {**GAME_BRIEF, "description": "…", "tags": ["Souls-like"], "playtime_hours": 60, "price_info": {}},
        ok_text="게임 상세", errors=(404, 422),
    ),
    "games_sync": spec(
        "Sync Games (게임 데이터 가져오기 · 관리자)",
        """
RAWG(+IGDB)에서 검색어에 맞는 게임을 가져와 `games` 테이블에 저장합니다. **헤더 `X-Admin-Token` 필요**(= `.env` 의 `ADMIN_TOKEN`).
Swagger 오른쪽 위 `Authorize` 가 아니라, 이 항목의 `Try it out` 안에 있는 `X-Admin-Token` 칸에 직접 입력하세요.
- `platform` 을 주면 해당 플랫폼 게임만 가져옵니다 (PS5 등은 공식 API가 없어 RAWG로 조회)
- `.env` 에 `RAWG_API_KEY` 또는 IGDB 키가 있어야 합니다.
- 저장 전에 **데이터를 정리**합니다: 장르 이름 통일(IGDB `Platform` → `Platformer` 등), 스팀 기능 태그(`Steam Achievements` 등) 제거, 스팀 앱 id 저장(리뷰 요약·가격 동기화용).
- 평가·추가 수가 거의 없는 **비공식 항목은 건너뛰고** `skipped` 에 알려줍니다. 꼭 필요하면 `include_minor: true`.
- RAWG 키가 틀리면 502(키 확인 안내), 인터넷 연결 문제면 503.
        """,
        {"saved": ["Hollow Knight"], "skipped": ["Hollow Knight-Scene Design"], "failed": []},
        ok_text="저장한 게임 / 건너뛴 비공식 항목 / 저장 실패 목록", errors=(403, 422, 502, 503),
    ),
    # ---------------- survey
    "survey_generate": spec(
        "Generate (레거시 심화 설문 AI 문장 생성)",
        """
프론트의 **심화 설문 28문항**을 Ollama가 사용자 상황에 맞게 자연스럽게 다시 써 줍니다. 질문의 의미·순서·id 는 바뀌지 않고 **문장만** 바뀝니다.
- `blueprint` : 프론트가 만든 28문항 구조(`E.publicBlueprint()` 결과). **꼭 필요합니다.**
- `request` : 사용자가 직접 입력한 요청 문장 / `profileContext` : 저장된 프로필의 6축 점수 (말투 참고용)
- AI가 문항을 잘못 쓰면 그 문항만 **원래 문장을 유지**합니다. 하나도 못 쓰면 502, Ollama가 꺼져 있으면 503 (프론트는 기본 문항으로 대체)
- 응답이 오래 걸릴 수 있습니다(최대 약 50초).
- Swagger에서 시험하려면 `blueprint` 칸에 `tests/fixtures/blueprints.json` 안의 `blueprint` 배열을 붙여넣으세요.
        """,
        {"questions": [{"id": "d01", "title": "다듬어진 질문 문장", "options": [{"id": "0", "label": "다듬어진 선택지"}]}],
         "source": "ollama", "rewritten": 28},
        ok_text="다듬어진 28문항", errors=(422, 502, 503),
    ),
    "survey_questions": spec(
        "List Questions (설문 문항 조회)",
        "선택한 대상(track)과 단계(stage)에 맞는 설문 문항을 question_no 순서로 조회합니다. 비회원도 문항을 읽을 수 있으며, 문항 데이터는 서버의 Supabase에서 관리합니다.",
        {"questions": [{"id": "gamer_onboarding_01", "track": "gamer", "stage": "onboarding", "question_no": 1, "question_text": "어떤 게임을 즐기시나요?", "options": []}]},
        ok_text="설문 문항 목록", errors=(422, 503),
    ),
    # ---------------- ai
    "ai_search": spec(
        "Natural Language Search (자연어 게임 검색 · 대체제 찾기)",
        """
문장으로 게임을 찾습니다. 예) `친구 3명이서 주말에 웃으면서 할 수 있는 사양 낮은 게임`, `스위치 없는데 동물의 숲 같은 게임 없어?`
- Ollama가 문장을 검색 조건으로 바꾸고(꺼져 있으면 키워드 규칙으로 대체), 점수·필터는 코드가 계산합니다.
- 한국어 게임 이름(`동물의 숲` 등)은 `data/game_aliases.json` 별칭표로 영어 제목을 찾습니다. 표에 없는 이름은 AI가 추측하며, 못 찾으면 `liked_games` 가 비어 장르·태그로만 검색합니다.
- 인디·할인·최근 같은 선호는 **문장에 그 말이 있을 때만** 반영합니다 (AI가 멋대로 켜지 않음). 점수가 너무 낮은 무관한 게임은 결과에서 뺍니다.
- "~같은 게임"에 나온 게임이 DB에 없으면 RAWG/IGDB에서 찾아 저장합니다(키가 있을 때).
- `explain=true` 면 상위 3개 중 점수가 충분한 결과에 AI가 추천 이유 문장을 씁니다(느리면 `false`). AI 문장에 게임에 없는 장르·태그 설명(예: 퍼즐이 아닌데 "퍼즐")이 있으면 버리고 기본 문장을 씁니다. `reason_source` 가 `ollama` / `rule` 로 구분됩니다.
        """,
        {"intent": {"liked_games": ["Animal Crossing: New Horizons"], "exclude_platforms": ["switch"], "source": "ollama"},
         "liked_games": ["Animal Crossing: New Horizons"], "liked_games_not_found": [], "results": [AI_RESULT_ITEM]},
        ok_text="검색 결과 (점수 높은 순)", errors=(422,),
    ),
    "ai_chat_recommendation": spec(
        "Conversational Recommendation (자유 대화형 AI 게임 추천)",
        "사용자와 Ollama가 자유롭게 대화하며 취향과 플레이 환경을 파악합니다. 정보가 충분해지면 PC·콘솔 지원이 확인된 게임 데이터에서 적합도 상위 5개를 검색하고 추천 이유를 반환합니다. profile 모드는 저장된 취향 프로필과 게임별 6축 점수를 반영하고, conversation 모드는 저장 프로필을 사용하지 않고 대화 내용만 누적합니다. Render 외부 게임 검색 결과와 내부 DB 후보를 함께 활용하며, 외부 서버 장애 시 내부 DB 후보로 대체합니다. Ollama 연결이 필요하며 실패 시 503을 반환합니다.",
        {"ready": True, "reply": "조건에 맞는 게임을 찾았어요.", "count": 1, "results": [AI_RESULT_ITEM]},
        ok_text="대화 응답 및 게임 추천 결과", errors=(422, 503),
    ),
    # ---------------- external games
    "external_games_search": spec(
        "External Game Search (\uc678\ubd80 \uac8c\uc784 \uac80\uc0c9)",
        "\uc678\ubd80 \uac8c\uc784 \ub370\uc774\ud130\ubca0\uc774\uc2a4\uc5d0\uc11c \uac8c\uc784 \uc774\ub984\uc73c\ub85c \uac80\uc0c9\ud569\ub2c8\ub2e4.\n- `q`\ub294 \uac80\uc0c9\ud560 \uac8c\uc784 \uc774\ub984\uc785\ub2c8\ub2e4.\n- `page`\ub294 \uc870\ud68c\ud560 \ud398\uc774\uc9c0 \ubc88\ud638\uc774\uba70 \uae30\ubcf8\uac12\uc740 1\uc785\ub2c8\ub2e4.\n- `size`\ub294 \ud398\uc774\uc9c0\ub2f9 \uacb0\uacfc \uc218\uc774\uba70 \uae30\ubcf8\uac12\uc740 20, \ucd5c\ub313\uac12\uc740 50\uc785\ub2c8\ub2e4.\n- \uc678\ubd80 \uac8c\uc784 \uac80\uc0c9 \uc11c\ubc84\uc5d0 \uc5f0\uacb0\ud560 \uc218 \uc5c6\uc73c\uba74 502 \uc624\ub958\ub97c \ubc18\ud658\ud569\ub2c8\ub2e4.",
        ok={
            "items": [{
                "id": "steam-1245620",
                "appid": 1245620,
                "title": "ELDEN RING",
                "name": "ELDEN RING",
                "header": "https://example.com/header.jpg",
                "platforms": ["PC", "PlayStation 5"],
                "source": "external",
            }]
        },
        ok_text="\uc678\ubd80 \uac8c\uc784 \uac80\uc0c9 \uacb0\uacfc", errors=(422, 502),
    ),
    "external_games_detail": spec(
        "External Game Detail (\uc678\ubd80 \uac8c\uc784 \uc0c1\uc138 \uc870\ud68c)",
        "\uc678\ubd80 \uac8c\uc784 \ub370\uc774\ud130\ubca0\uc774\uc2a4\uc5d0\uc11c \uc9c0\uc815\ud55c \uac8c\uc784\uc758 \uc0c1\uc138 \uc815\ubcf4\ub97c \uc870\ud68c\ud569\ub2c8\ub2e4.\n- `appid`\ub294 \uc870\ud68c\ud560 \uac8c\uc784\uc758 \uc678\ubd80 \ub370\uc774\ud130\ubca0\uc774\uc2a4 ID\uc785\ub2c8\ub2e4.\n- \uac8c\uc784\uc744 \ucc3e\uc744 \uc218 \uc5c6\uac70\ub098 PC \ub610\ub294 \ucf58\uc194 \ubc84\uc804\uc774 \uc5c6\uc73c\uba74 404 \uc624\ub958\ub97c \ubc18\ud658\ud569\ub2c8\ub2e4.\n- \uc678\ubd80 \uac8c\uc784 \uc815\ubcf4 \uc11c\ubc84\uc5d0 \uc5f0\uacb0\ud560 \uc218 \uc5c6\uc73c\uba74 502 \uc624\ub958\ub97c \ubc18\ud658\ud569\ub2c8\ub2e4.",
        ok={
            "appid": 1245620,
            "steam": {
                "name": "ELDEN RING",
                "header_image": "https://example.com/header.jpg",
            },
            "igdb": {
                "game": {
                    "platforms": ["PC", "PlayStation 5"],
                }
            },
        },
        ok_text="\uc678\ubd80 \uac8c\uc784 \uc0c1\uc138 \uc815\ubcf4", errors=(404, 422, 502),
    ),
    # ---------------- market
    "market": spec(
        "Market (스팀 인기 순위·소식·리뷰 집계)",
        """
프론트의 **랭킹·뉴스 화면**이 부르는 API입니다. `section` 으로 가져올 묶음을 고릅니다. 응답은 항상 `{section, updatedAt, data}` 형태이고 `updatedAt` 은 스팀에서 가져온 시각입니다.
- `rankings` : 스팀 동시 접속 인기 순위 상위 10개. `players` 는 지금 접속자 수이고, 못 가져오면 `null`(화면에는 '집계 대기')
- `news` : `data` 안에 `news`(공식 소식), `newReleases`(신작), `sales`(할인). `game` 을 주면 `news` 는 그 게임 것만, 안 주면 대표 게임 12개의 소식
- `reviews` : 전체 언어 리뷰 집계(`positive`·`negative`·`total`·`description`). **`game` 필수**

`game` 은 프론트 게임 id(예: `elden`)입니다. 가격은 최소 화폐 단위라 `2745000` = 27,450원입니다.
스팀을 자주 부르지 않도록 결과를 10~30분 보관합니다. 스팀이 응답하지 않으면 502를 돌려줍니다.
        """,
        {"section": "rankings", "updatedAt": "2026-10-03T09:00:00+00:00",
         "data": [{"rank": 1, "app": 730, "name": "Counter-Strike 2", "players": 1012345,
                   "url": "https://store.steampowered.com/app/730/"}]},
        ok_text="요청한 묶음의 최신 자료", errors=(404, 422, 502),
    ),
    "steam_reviews": spec(
        "Steam Reviews (스팀 플레이어 리뷰 목록)",
        """
게임 상세 화면의 리뷰 목록입니다. 한 번에 12개씩 오고, 응답의 `cursor` 를 다음 요청의 `cursor` 로 넣으면 이어서 가져옵니다(`cursor` 가 `null` 이면 끝).
- `sentiment` 추천/비추천, `language` 리뷰 언어, `sort` 최신순/도움순, `days` 작성 기간으로 거릅니다.
- 리뷰 글은 600자까지만 보내고, 더 길면 `truncated: true` 입니다.
결과는 5분간 보관합니다.
        """,
        {"items": [{"id": "236761964", "text": "정말 재미있어요", "truncated": False, "positive": True,
                    "created": 1791012880, "updated": 1791012880, "language": "koreana", "hours": 165.7,
                    "helpful": 3, "purchased": True, "receivedFree": False,
                    "url": "https://steamcommunity.com/profiles/76561198000000000/recommended/1245620/"}],
         "cursor": "AoJworCFgKEDcbaShwc=", "checkedAt": "2026-10-03T09:00:00+00:00"},
        ok_text="리뷰 12개와 다음 페이지 표식", errors=(404, 422, 502),
    ),
    "steam_details": spec(
        "Steam Details (스팀 가격·사양 갱신)",
        """
게임 상세 화면의 '가격·정보 갱신' 버튼이 부릅니다. 개발사·배급사·출시일·한국어 지원·지원 OS·최소/권장 사양·현재 가격을 스팀에서 가져옵니다.
`price` 의 금액은 최소 화폐 단위입니다(`6480000` = 64,800원). 스크린샷은 보내지 않으며, 프론트가 가진 기존 값이 그대로 유지됩니다. 결과는 1시간 보관합니다.
        """,
        {"details": {"developers": ["FromSoftware, Inc."], "publishers": ["Bandai Namco Entertainment"],
                     "releaseDate": "2022년 2월 24일", "korean": True, "languages": "영어*, 한국어",
                     "os": {"windows": True, "mac": False, "linux": False},
                     "minimum": [["운영 체제", "Windows 10"]], "recommended": [["운영 체제", "Windows 10/11"]],
                     "price": {"price": 6480000, "originalPrice": 6480000, "discount": 0, "currency": "KRW"},
                     "checkedAt": "2026-10-03T09:00:00+00:00"}},
        ok_text="갱신된 게임 정보", errors=(404, 422, 502),
    ),
}
