"""검색 품질 개선 회귀 테스트: 실제 7B 응답(tests/fixtures/ai_search_real_response.json)에서 발견한 문제들.
(fastapi/Ollama 불필요)   python -m tests.test_search_quality"""
import asyncio
import json
from datetime import date
from pathlib import Path

from app.mock_db import MockSupabase
from app.services import ai_features as ai
from app.services import aliases

TODAY = date(2026, 10, 2)
GAMES = MockSupabase().table("games").select("*").execute().data
VOCAB = ai.vocabulary(GAMES)
FX = json.loads((Path(__file__).parent / "fixtures" / "ai_search_real_response.json").read_text(encoding="utf-8"))


def llm_returning(payload):
    async def _llm(system, user, temperature=0.3):
        if isinstance(payload, Exception):
            raise payload
        return payload
    return _llm


def game(name):
    return next(g for g in GAMES if g["title"] == name)


# ---------- 1) 한국어 게임 이름 별칭 ----------
def test_aliases():
    assert aliases.find_in_text("스위치 없는데 동물의 숲 같은 게임 없어?") == ["Animal Crossing: New Horizons"]
    assert aliases.find_in_text("발더스 게이트 3 같은 거") == ["Baldur's Gate 3"]  # 긴 별칭 우선(발더스 게이트 X)
    assert aliases.find_in_text("컨트롤이 쉬운 게임") == []                          # 짧은 단어 속 오탐 방지
    assert aliases.canonical("스타듀 밸리") == "Stardew Valley" and aliases.canonical("Hades") == "Hades"
    assert ai.find_game(GAMES, "동물의 숲")["title"] == "Animal Crossing: New Horizons"
    assert ai.find_game(GAMES, "엘든링")["title"] == "Elden Ring"


# ---------- 2) 실제 7B 응답을 그대로 넣었을 때 ----------
def _parse_real():
    return asyncio.run(ai.parse_search_intent(FX["query"], VOCAB, GAMES, llm_returning(FX["llm_raw_intent"])))


def test_real_response_intent_is_corrected():
    it = _parse_real()
    assert it["liked_games"] == ["Animal Crossing: New Horizons"]      # 7B는 비워 뒀지만 별칭표가 찾음
    assert not any(it["prefer"].values())                              # 7B가 지어낸 indie/cheap 제거
    assert it["platforms"] == [] and it["exclude_platforms"] == ["switch"]  # 언급 안 한 기기 나열 제거
    assert it["genres"] == [] and it["tags"] == []                     # 기준 게임이 있으면 7B가 고른 장르/태그(Puzzle 등) 무시


def test_real_response_results_are_clean():
    it = _parse_real()
    liked = [ai.find_game(GAMES, t) for t in it["liked_games"]]
    res = ai.search_games(GAMES, it, liked, TODAY, 10)
    names = [r["game"]["title"] for r in res]
    assert "Stardew Valley" in names
    assert not any("할인 중" in r["matched"] for r in res)             # 할인 가산점 왜곡 없음
    assert not {"Resident Evil Village", "Elden Ring", "Portal 2", "Hades", "Celeste"} & set(names)  # 무관한 게임 제거
    top = res[0]["score"]
    assert all(r["score"] >= max(min(ai.MIN_SCORE, top), top * ai.MIN_RATIO) for r in res)
    for r in res:  # 스위치 없는 사람이 할 수 있는 게임만
        assert ai.platform_keys(r["game"]["platforms"]) - {"switch"}


# ---------- 3) LLM이 지어내는 기기/선호를 걸러냄 ----------
def test_unmentioned_platforms_are_dropped_but_mentioned_are_kept():
    raw = {"liked_games": [], "platforms": ["pc", "ios"], "exclude_platforms": ["xbox"],
           "prefer": {"indie": True, "cheap": True}, "genres": [], "tags": ["Cozy"]}
    it = asyncio.run(ai.parse_search_intent("힐링 게임 추천해줘", VOCAB, GAMES, llm_returning(raw)))
    assert it["platforms"] == [] and it["exclude_platforms"] == [] and not any(it["prefer"].values())
    it = asyncio.run(ai.parse_search_intent("PC로 할 수 있는 힐링 게임, 스위치는 없어", VOCAB, GAMES,
                                            llm_returning({**raw, "platforms": ["pc"], "exclude_platforms": ["switch"]})))
    assert it["platforms"] == ["pc"] and it["exclude_platforms"] == ["switch"]


def test_prefer_follows_keywords_only():
    it = asyncio.run(ai.parse_search_intent("저렴한 인디 게임", VOCAB, GAMES, llm_returning({"liked_games": []})))
    assert it["prefer"]["cheap"] and it["prefer"]["indie"] and not it["prefer"]["recent"]


# ---------- 4) 흔한 태그 가중치 ----------
def test_generic_tags_count_less():
    a = {"genres": [], "tags": ["Singleplayer", "Cozy"]}
    b = {"genres": [], "tags": ["Singleplayer", "Horror"]}
    assert ai.similarity(a, b) < 0.2   # 가중치 없이 계산하면 0.33
    intent = {"genres": [], "tags": ["Singleplayer", "Atmospheric"], "platforms": [], "exclude_platforms": [], "prefer": {}, "max_hours": None}
    res = ai.search_games(GAMES, intent, [], TODAY, 30)
    assert res and all(r["score"] <= 2 * ai.GENERIC_TAG_WEIGHT for r in res)  # 흔한 태그만으로는 높은 점수가 안 나온다
    assert len({r["score"] for r in res}) == 1   # 요청이 흔한 태그뿐이어도 빈 결과 대신 최고 점수대를 돌려준다


# ---------- 5) 추천 이유 환각 방지 ----------
def test_unsupported_claims_detected_on_real_hallucination():
    portal = game("Portal 2")
    real_text = next(r["reason"] for r in FX["old_results"] if r["title"] == "Portal 2")
    assert ai.unsupported_claims(real_text, portal)                     # '추리 퍼즐' 은 근거 태그 없음 -> 환각
    assert ai.unsupported_claims("[Portal 2]는 퍼즐을 풀며 협동도 가능해요.", portal) == []
    terraria_text = next(r["reason"] for r in FX["old_results"] if r["title"] == "Terraria")
    assert ai.unsupported_claims(terraria_text, game("Terraria")) == []  # 탐험/제작/협동 은 태그로 뒷받침됨


def test_explain_rejects_hallucinated_or_titleless_text():
    portal = game("Portal 2")
    fallback = ai.rule_reason(portal, ["Puzzle", "Adventure"])
    real_text = next(r["reason"] for r in FX["old_results"] if r["title"] == "Portal 2")
    text, src = asyncio.run(ai.explain_game({}, portal, fallback, llm_returning({"text": real_text}), matched=["Puzzle"]))
    assert (text, src) == (fallback, "rule")
    titleless = "머리를 쓰는 퍼즐을 좋아하는 분께 잘 맞는 게임이에요. 협동도 가능해요."
    assert asyncio.run(ai.explain_game({}, portal, fallback, llm_returning({"text": titleless})))[1] == "rule"
    good = "[Portal 2]는 퍼즐을 풀면서 친구와 협동도 할 수 있는 게임이에요."
    assert asyncio.run(ai.explain_game({}, portal, fallback, llm_returning({"text": good}), matched=["Puzzle", "Co-op"])) == (good, "ollama")


def test_rule_reason_handles_discount_naturally():
    text = ai.rule_reason(game("Hades"), ["Roguelike", "Indie", "할인 중"])
    assert "Roguelike, Indie 요소" in text and text.endswith("지금 할인 중이에요.") and "할인 중 요소" not in text


def test_matched_lists_important_tags_first():
    intent = {"genres": [], "tags": ["Singleplayer", "Roguelike"], "platforms": [], "exclude_platforms": [], "prefer": {}, "max_hours": None}
    res = ai.search_games(GAMES, intent, [], TODAY, 5)
    hades = next(r for r in res if r["game"]["title"] == "Hades")
    assert hades["matched"][0] == "Roguelike" and hades["matched"][-1] == "Singleplayer"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
