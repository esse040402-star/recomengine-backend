"""Swagger(/docs) 화면에 보이는 한국어 설명을 한곳에 모아둔 파일.
설명을 고치고 싶으면 이 파일만 수정하면 됩니다. 라우터는 `@router.get("/경로", **doc("키"))` 형태로 가져다 씁니다."""

# ---------------------------------------------------------------- 태그(그룹 제목)
SYSTEM = "system (서버 상태)"
ACCOUNT = "account (회원·로그인)"
SESSIONS = "sessions (취향 진단)"
SURVEY = "survey (설문 생성 AI)"
GAMES = "games (게임 목록)"
AI = "ai (AI 검색·추천)"

OPENAPI_TAGS = [
    {"name": SYSTEM, "description": "서버와 AI(Ollama)가 정상인지 확인합니다."},
    {"name": ACCOUNT, "description": "회원가입, 로그인, 로그아웃, 내 화면 상태 저장. 로그인 상태는 쿠키로 유지됩니다."},
    {"name": SESSIONS, "description": "취향 진단 한 번 = 세션 하나. **시작 → 답변 저장 → 완료(점수·리포트·추천 생성) → 결과 조회** 순서로 사용합니다."},
    {"name": SURVEY, "description": "심화 설문 28문항의 문장을 Ollama(AI)가 사용자 상황에 맞게 다듬습니다."},
    {"name": GAMES, "description": "DB에 저장된 게임 목록·상세 조회, 그리고 RAWG/IGDB에서 게임 데이터를 가져오는 관리자 기능."},
    {"name": AI, "description": "자연어 검색, 비슷한 게임/대체제, 추천 이유, 백로그 처리반, 플레이타임 계산기, 리뷰 요약, 할인·출시예정 정렬. "
                                "문장 이해·작성은 Ollama가 하고 점수·필터·일정 계산은 코드가 합니다. **Ollama가 꺼져 있어도 대부분 규칙 기반으로 동작합니다.**"},
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
- `feeds` : 스팀 랭킹·뉴스 실시간 연동 여부 (아직 만들지 않아서 항상 `false`)
- `ollama` : `up`(Ollama 실행 중인지), `model`(`.env`에 설정한 모델), `model_ready`(그 모델이 설치됐는지)
- `rawg` / `igdb` / `steam` : 해당 API 키가 `.env`에 들어 있는지
- `mock_db` : `true` 면 Supabase 대신 **메모리 가짜 DB**로 동작 중 (서버를 끄면 데이터 삭제)
        """,
        {"ai": False, "feeds": False, "ollama": {"up": False, "model": "qwen2.5:7b", "model_ready": False},
         "rawg": False, "igdb": False, "steam": False, "mock_db": True},
        ok_text="현재 서버 상태",
    ),
    # ---------------- account
    "account_session": spec(
        "Get Session (현재 로그인 상태 확인)",
        """
쿠키를 보고 지금 로그인되어 있는지 알려줍니다. 프론트는 페이지를 열 때 호출합니다.
- 로그인 안 됨: `{"user": null}`
- 로그인 됨: `user`(id, 닉네임)와, 이전에 저장해 둔 화면 상태가 있으면 `state` 도 함께 돌려줍니다.
        """,
        {"user": {"id": UID, "name": "지헌"}, "state": {"track": "gamer", "quick": {"completed": True}}},
        ok_text="로그인 상태 (로그인 안 됐으면 user 가 null)",
    ),
    "account_signup": spec(
        "Signup (회원가입)",
        """
닉네임·이메일·비밀번호(8자 이상)로 가입하고 **바로 로그인 상태**가 됩니다(쿠키 발급).
비밀번호는 Supabase가 암호화해서 보관하며 이 서버는 저장하지 않습니다.
이미 가입된 이메일이면 409를 돌려줍니다. 이메일 인증 없이 바로 사용할 수 있습니다.
        """,
        {"user": {"id": UID, "name": "지헌"}}, ok_code=201, ok_text="가입 완료 (자동 로그인)", errors=(409, 422, 502),
    ),
    "account_login": spec(
        "Login (로그인)",
        """
이메일·비밀번호로 로그인합니다. 성공하면 쿠키가 발급되고, 이전에 저장해 둔 화면 상태가 있으면 `state` 로 함께 돌려줍니다.
- 이메일 또는 비밀번호가 틀리면 401 (어느 쪽이 틀렸는지는 알려주지 않습니다)
- **8번 연속 실패하면 15분 동안 429** 로 막습니다 (올바른 비밀번호도 거부)
        """,
        {"user": {"id": UID, "name": "지헌"}, "state": {"track": "gamer"}}, ok_text="로그인 성공", errors=(401, 422, 429, 502, 503),
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
- `prefs` : 사용자가 고른 조건. `platforms`(pc/console/mobile/umpc), `avoid`(horror/pvp/difficulty/mature/monetization…), `lowSpec`(저사양 선호)
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
        "Generate (심화 설문 AI 문장 생성)",
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
    "ai_similar": spec(
        "Similar Games (비슷한 게임 · 대체제 찾기)",
        """
재밌게 한 게임(들)과 **비슷한 게임**을 찾습니다.
- `prefer` : `indie`(인디), `cheap`(할인 중), `recent`(최근 3년), `short`(짧은 게임), `low_spec`(가벼운 게임), `coop`(협동)
- `exclude_platforms` : 없는 기기 (예: `["switch"]` → 스위치에서만 할 수 있는 게임은 제외)
- 입력한 게임을 DB에서 못 찾으면 404 입니다.
        """,
        {"liked_games": ["Elden Ring"], "liked_games_not_found": [], "results": [AI_RESULT_ITEM]},
        ok_text="비슷한 게임 목록", errors=(404, 422),
    ),
    "ai_explain": spec(
        "Explain Recommendation (추천 이유 AI 설명)",
        """
진단 결과로 추천된 게임에 대해 **AI가 쓴 추천 이유 문장**을 만들고, DB(`recommendations.reason`)에도 저장합니다.
- 그 세션의 추천 목록에 있는 게임이어야 합니다(없으면 404).
- Ollama가 꺼져 있으면 기존 문장을 그대로 돌려줍니다(`source: "rule"`).
        """,
        {"reason": "퇴근 후 편하게 쉬고 싶은 분께 [Stardew Valley]의 잔잔한 농장 생활을 추천해요.", "source": "ollama"},
        ok_text="추천 이유", errors=(401, 403, 404, 422),
    ),
    "ai_backlog": spec(
        "Backlog Picker (백로그 처리반 · 오늘 할 게임 고르기)",
        """
내 라이브러리에서 **지금 기분과 시간에 맞는 게임 하나**를 골라줍니다.
- `games` : 가지고 있는 게임 제목 목록(5~10개 이상) 또는 `steam_id`(17자리 SteamID64, 서버에 `STEAM_API_KEY` 필요, 프로필 공개 필요)
- `mood` : 지금 기분 (예: `머리 비우고 싶어`) / `minutes` : 쓸 수 있는 시간(분)
- 고른 게임은 반드시 입력한 목록 안에서만 나옵니다. Ollama가 꺼져 있으면 규칙 기반으로 고릅니다.
        """,
        {"pick": {"title": "Vampire Survivors", "genres": ["Action"], "tags": ["Roguelite"], "playtime_hours": 6},
         "reason": "30분 단판으로 가볍게 스트레스를 풀기 좋아요.", "source": "ollama", "candidates_considered": 3, "matched_in_db": 2},
        ok_text="오늘의 게임", errors=(422, 502, 503),
    ),
    "ai_schedule": spec(
        "Play Schedule (플레이타임 계산기 · 엔딩 일정)",
        """
게임 엔딩까지 걸리는 시간과 내 여유 시간으로 **현실적인 일정**을 계산합니다. 계산은 코드가 하고, 설명 문장만 AI가 씁니다.
- 게임은 `game_id` 또는 `title` 로 지정합니다.
- 시간은 `text`(예: `주말에 하루 2시간씩`) 또는 `hours_per_day` + `days_per_week` 로 줍니다.
- 플레이타임은 RAWG 등의 **평균값**이라 실제와 다를 수 있습니다. 데이터가 없는 게임은 422 입니다.
- 엔딩까지 4주를 넘으면 더 짧은 비슷한 게임도 함께 추천합니다.
        """,
        {"game": GAME_BRIEF, "plan": {"playtime_hours": 60, "hours_per_day": 2, "days_per_week": 2, "weekly_hours": 4, "play_sessions": 30,
                                      "weeks": 15.0, "finish_date": "2027-01-15"},
         "assumptions": [], "shorter_alternatives": [], "message": "주 4시간씩 하면 엔딩까지 약 15주예요.", "message_source": "ollama",
         "note": "플레이타임은 RAWG 등 외부 데이터의 평균값이라 실제와 다를 수 있어요."},
        ok_text="계산된 일정", errors=(404, 422),
    ),
    "ai_review": spec(
        "Review Summary (리뷰 장단점 요약)",
        """
리뷰를 읽고 **장점·단점·한 줄 총평**으로 요약합니다.
- `reviews` 에 리뷰 문장을 직접 넣거나(3개 이상), 비워두면 게임에 `steam_app_id` 가 있을 때 스팀 공개 리뷰를 가져옵니다.
- 이 기능은 AI가 꼭 필요해서, Ollama가 꺼져 있으면 503 입니다.
        """,
        {"game": {"id": GID, "title": "Hades"}, "pros": ["전투가 재미있다"], "cons": ["최적화가 아쉽다"],
         "verdict": "전반적으로 호평", "review_count": 3},
        ok_text="리뷰 요약", errors=(404, 422, 502, 503),
    ),
    "ai_deals": spec(
        "Personalized Deals (취향 맞춤 할인·출시예정 게임)",
        """
진단 결과(6개 성향)와 잘 맞는 **할인 중 게임**과 **출시 예정 게임**을 위로 정렬해서 보여줍니다.
- 진단을 먼저 완료해야 합니다(안 했으면 409).
- 할인 정보는 `games.price_info` 에 가격이 들어 있어야 보입니다(관리자 가격 동기화 API 사용).
        """,
        {"deals": [{"game": GAME_BRIEF, "match_score": 80.0, "discount_percent": 30, "final_price": "₩16,800",
                    "matched_tags": ["Roguelike"], "rank_score": 83.0}],
         "upcoming": [{"game": GAME_BRIEF, "match_score": 77.0, "release_date": "2027-03-01", "matched_tags": ["Cozy"]}]},
        ok_text="할인 중·출시 예정 게임", errors=(401, 403, 404, 409, 422),
    ),
    "ai_sync_prices": spec(
        "Sync Prices (스팀 가격 동기화 · 관리자)",
        """
`steam_app_id` 가 있는 게임의 가격·할인율을 스팀에서 가져와 `games.price_info` 에 저장합니다. **헤더 `X-Admin-Token` 필요**.
`cc` 는 국가 코드(기본 `kr` = 한국 원화)입니다.
        """,
        {"games_with_steam_id": 1, "updated": 1}, ok_text="갱신한 게임 수", errors=(403, 422),
    ),
}
