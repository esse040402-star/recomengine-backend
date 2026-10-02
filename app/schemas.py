from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Track = Literal["gamer", "nongamer"]
EX_SESSION = "3f2b8c1e-0000-4000-8000-000000000001"
EX_GAME = "9a7d5e42-0000-4000-8000-0000000000aa"


def example(*items: dict) -> ConfigDict:
    """Swagger의 'Try it out' 입력칸에 처음부터 채워져 있을 예시 값."""
    return ConfigDict(json_schema_extra={"examples": list(items)})


# ---------- 진단 세션 ----------
class SessionCreate(BaseModel):
    model_config = example({"track": "gamer"})
    track: Track = Field(description="`gamer`(게임을 즐기는 사람) 또는 `nongamer`(게임이 낯선 사람)")


class AnswerIn(BaseModel):
    question_id: str = Field(min_length=1, max_length=64, description="프론트의 질문 id (예: `q1`, `d01`)")
    answer: Any = Field(description="선택한 선택지 id 목록 등 (JSON이면 무엇이든 가능, null 은 불가)")

    @field_validator("answer")
    @classmethod
    def not_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("answer는 null일 수 없습니다.")
        return v


class AnswersIn(BaseModel):
    model_config = example({"answers": [{"question_id": "q1", "answer": ["0"]}, {"question_id": "q2", "answer": ["1"]}]})
    answers: list[AnswerIn] = Field(min_length=1, max_length=150, description="저장할 답변 목록 (같은 질문은 덮어씀)")


class CompleteIn(BaseModel):
    model_config = example({
        "axes": [90, 50, 60, 60, 15, 70],
        "title": "손맛을 즐기는 도전자",
        "prefs": {"platforms": ["pc"], "avoid": ["horror"], "lowSpec": False},
        "evidence": [{"question": "전투 시스템에서 피지컬 요구치는?", "answer": "정교한 숙련도"}],
    })
    axes: list[float] = Field(
        min_length=6, max_length=6,
        description="6개 성향 점수(각 0~100). 순서: [조작·피지컬, 전략·문제 해결, 탐색·수집, 감성·몰입, 휴식·힐링, 경쟁·성취]",
    )
    title: str | None = Field(default=None, max_length=60, description="프론트가 정한 성향 유형 이름 (예: 손맛을 즐기는 도전자)")
    prefs: dict[str, Any] = Field(
        default_factory=dict,
        description="사용자가 고른 조건. `platforms`(pc/console/mobile/umpc), `avoid`(horror/pvp/difficulty/mature/monetization 등), `lowSpec`(true/false)",
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list, max_length=80,
        description="리포트 작성에 참고할 질문·답변 목록 (`question`, `answer` 글자). 비워도 됨",
    )

    @field_validator("axes")
    @classmethod
    def in_range(cls, v: list[float]) -> list[float]:
        if any(x < 0 or x > 100 for x in v):
            raise ValueError("axes 값은 0~100 이어야 합니다.")
        return v


# ---------- 설문 생성 ----------
class BlueprintOption(BaseModel):
    id: str = Field(description="선택지 id")
    label: str = Field(description="선택지 문장")


class BlueprintQuestion(BaseModel):
    id: str = Field(description="질문 id (예: d01)")
    field: str | None = Field(default=None, description="질문이 측정하는 항목 이름")
    title: str = Field(description="질문 문장")
    options: list[BlueprintOption] = Field(description="선택지 목록")


class ProfileContext(BaseModel):
    axes: list[float] = Field(min_length=6, max_length=6, description="저장된 프로필의 6개 성향 점수")
    prefs: dict[str, Any] = Field(default_factory=dict, description="저장된 프로필의 조건(플랫폼, 불호 요소 등)")


class SurveyGenerateIn(BaseModel):
    model_config = example({"track": "gamer", "answers": {"q1": ["0"]}, "request": "혼자 편하게 즐길 무료 게임을 찾고 있어요"})
    track: Track = Field(description="`gamer` 또는 `nongamer`")
    answers: dict[str, list[str]] = Field(default_factory=dict, description="기본 7문항 답변 (질문 id → 선택지 id 목록)")
    request: str = Field(default="", max_length=300, description="사용자가 직접 입력한 요청 문장 (없으면 빈 글자)")
    profileContext: ProfileContext | None = Field(default=None, description="저장된 프로필을 반영할 때만 보냄")
    blueprint: list[BlueprintQuestion] | None = Field(
        default=None,
        description="프론트가 만든 28문항 구조 (`E.publicBlueprint(track, answers)` 결과). **필수.** "
                    "Swagger에서 시험하려면 `tests/fixtures/blueprints.json` 의 blueprint 배열을 붙여넣으세요.",
    )


# ---------- 관리자 ----------
class GameSyncIn(BaseModel):
    model_config = example({"query": "elden ring", "limit": 5, "platform": "pc"})
    query: str = Field(min_length=1, max_length=100, description="검색할 게임 이름 (영어 권장)")
    limit: int = Field(default=10, ge=1, le=20, description="가져올 게임 개수 (최대 20)")
    platform: Literal["pc", "ps5", "ps4", "xbox", "switch", "ios", "android"] | None = Field(
        default=None, description="특정 플랫폼 게임만 가져오기 (비우면 전체). PS5 등은 공식 API가 없어 RAWG로 조회",
    )
    include_minor: bool = Field(
        default=False, description="평가·추가 수가 거의 없는 비공식 항목(팬 제작물 등)도 가져올지. 보통은 false",
    )


# ---------- AI 기능 ----------
class AiSearchIn(BaseModel):
    model_config = example({"query": "스위치 없는데 동물의 숲 같은 게임 없어?", "limit": 10, "explain": True})
    query: str = Field(min_length=2, max_length=200, description="찾고 싶은 게임을 평소 말투로 (2~200자)")
    limit: int = Field(default=10, ge=1, le=30, description="돌려받을 결과 개수")
    explain: bool = Field(default=True, description="상위 3개에 AI 추천 이유 문장 생성 (느리면 false)")


class SimilarIn(BaseModel):
    model_config = example({"titles": ["Elden Ring"], "prefer": ["cheap"], "exclude_platforms": [], "platforms": [], "limit": 10, "explain": True})
    titles: list[str] = Field(min_length=1, max_length=5, description="재밌게 한 게임 제목 (1~5개, 영어 제목 권장)")
    prefer: list[Literal["indie", "cheap", "recent", "short", "low_spec", "coop"]] = Field(
        default_factory=list,
        description="원하는 성격: `indie`(인디) `cheap`(할인 중) `recent`(최근 3년) `short`(짧은 게임) `low_spec`(가벼운 게임) `coop`(협동)",
    )
    exclude_platforms: list[str] = Field(default_factory=list, max_length=6, description="없는 기기 (예: `switch`, `pc`, `playstation`, `xbox`, `ios`, `android`)")
    platforms: list[str] = Field(default_factory=list, max_length=6, description="쓸 수 있는 기기만 보기 (비우면 전체)")
    limit: int = Field(default=10, ge=1, le=30, description="돌려받을 결과 개수")
    explain: bool = Field(default=True, description="상위 3개에 AI 추천 이유 문장 생성")

    @field_validator("titles")
    @classmethod
    def clean_titles(cls, v: list[str]) -> list[str]:
        v = [t.strip() for t in v if t and t.strip()]
        if not v or any(len(t) > 100 for t in v):
            raise ValueError("titles 는 1~100자의 게임 제목이어야 합니다.")
        return v


class ExplainIn(BaseModel):
    model_config = example({"session_id": EX_SESSION, "game_id": EX_GAME})
    session_id: UUID = Field(description="진단 세션 id (세션 시작 API 응답의 id). 예시 값은 꼭 실제 값으로 바꾸세요")
    game_id: UUID = Field(description="그 세션의 추천 결과에 있는 게임 id (결과 조회 API의 `games.id`)")


class BacklogIn(BaseModel):
    model_config = example({"games": ["Elden Ring", "Vampire Survivors", "Stardew Valley"], "mood": "퇴근하고 머리 비우고 싶어", "minutes": 60})
    games: list[str] = Field(default_factory=list, max_length=300, description="가지고 있는 게임 제목 목록 (5~10개 이상 권장)")
    steam_id: str | None = Field(default=None, max_length=32, description="스팀 17자리 ID(SteamID64). 서버에 `STEAM_API_KEY` 가 있고 프로필이 공개일 때만")
    mood: str = Field(default="", max_length=120, description="지금 기분/원하는 느낌 (예: 머리 비우고 싶어)")
    minutes: int = Field(default=60, ge=5, le=720, description="지금 쓸 수 있는 시간(분)")

    @field_validator("games")
    @classmethod
    def clean_games(cls, v: list[str]) -> list[str]:
        out = []
        for t in v:
            t = (t or "").strip()
            if t:
                if len(t) > 100:
                    raise ValueError("게임 제목은 100자 이하여야 합니다.")
                out.append(t)
        return out


class ScheduleIn(BaseModel):
    model_config = example({"title": "Baldur's Gate 3", "text": "주말에 하루 2시간씩 쓸 수 있어"})
    game_id: UUID | None = Field(default=None, description="게임 id (목록 API의 id). `title` 과 둘 중 하나만 있으면 됨")
    title: str | None = Field(default=None, max_length=100, description="게임 제목 (DB에 없으면 RAWG/IGDB에서 찾아봄)")
    text: str | None = Field(default=None, max_length=120, description="쓸 수 있는 시간을 말로 (예: `주말에 하루 2시간씩`, `매일 30분`, `주 6시간`)")
    hours_per_day: float | None = Field(default=None, gt=0, le=24, description="하루에 쓰는 시간. `text` 대신 직접 입력할 때")
    days_per_week: float | None = Field(default=None, gt=0, le=7, description="일주일에 플레이하는 날 수. 비우면 매일(7)로 가정")


class ReviewSummaryIn(BaseModel):
    model_config = example({"game_id": EX_GAME, "reviews": ["전투가 정말 재미있어요", "후반부 최적화가 아쉬워요", "스토리와 연출이 훌륭합니다"]})
    game_id: UUID = Field(description="게임 id (목록 API의 id). 예시 값은 실제 값으로 바꾸세요")
    reviews: list[str] | None = Field(
        default=None, max_length=60,
        description="요약할 리뷰 문장 (3개 이상). 비우면 게임에 `steam_app_id` 가 있을 때 스팀 공개 리뷰를 가져옴",
    )
