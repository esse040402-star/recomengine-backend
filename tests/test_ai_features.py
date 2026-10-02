"""AI 기능 로직 단위 테스트 (Ollama·fastapi 불필요, LLM은 가짜로 주입).
실행: python -m tests.test_ai_features   또는 pytest"""
import asyncio
from datetime import date

from app.mock_db import MockSupabase
from app.services import ai_features as ai

TODAY = date(2026, 10, 2)
GAMES = MockSupabase().table("games").select("*").execute().data
VOCAB = ai.vocabulary(GAMES)


def llm_returning(payload):
    async def _llm(system, user, temperature=0.3):
        if isinstance(payload, Exception):
            raise payload
        return payload
    return _llm


def title(name):
    return next(g for g in GAMES if g["title"] == name)


# ---------- 검색어 이해 ----------
def test_rule_intent_without_llm():
    intent = asyncio.run(ai.parse_search_intent(
        "친구 3명이서 주말에 웃으면서 할 수 있는 사양 낮은 게임", VOCAB, GAMES, llm_returning(RuntimeError("ollama down"))))
    assert intent["source"] == "rule"
    assert intent["prefer"]["coop"] and intent["prefer"]["low_spec"]
    assert "Co-op" in intent["tags"]


def test_intent_uses_vocabulary_only():
    # 좋아하는 게임이 없는 검색: LLM의 장르/태그를 쓰되, DB에 없는 단어는 버린다
    raw = {"liked_games": [], "genres": ["Not A Genre"], "tags": ["Cozy", "ZZZ"], "platforms": [],
           "exclude_platforms": [], "max_hours": 20}
    intent = asyncio.run(ai.parse_search_intent("아기자기하고 편안한 게임 추천", VOCAB, GAMES, llm_returning(raw)))
    assert intent["source"] == "ollama" and intent["max_hours"] == 20
    assert intent["tags"][0] == "Cozy" and "ZZZ" not in intent["tags"] and intent["genres"] == []


def test_switch_exclusion_rule():
    intent = ai.rule_intent("스위치 없는데 힐링 게임", VOCAB, GAMES)
    assert intent["exclude_platforms"] == ["switch"]


# ---------- 대체제 찾기 ----------
def test_alternative_to_switch_game():
    raw = {"liked_games": ["Animal Crossing: New Horizons"], "exclude_platforms": ["switch"], "tags": [], "genres": []}
    intent = asyncio.run(ai.parse_search_intent("스위치 없는데 동물의 숲 같은 게임 없어?", VOCAB, GAMES, llm_returning(raw)))
    liked = [ai.find_game(GAMES, t) for t in intent["liked_games"]]
    assert liked[0]["title"] == "Animal Crossing: New Horizons"
    res = ai.search_games(GAMES, intent, liked, TODAY, 5)
    names = [r["game"]["title"] for r in res]
    assert "Animal Crossing: New Horizons" not in names
    assert "Stardew Valley" in names[:3]
    for r in res:  # 스위치 말고도 할 수 있는 게임만
        assert ai.platform_keys(r["game"]["platforms"]) - {"switch"}


def test_unreleased_games_excluded_from_search():
    intent = {"genres": ["Simulation"], "tags": ["Cozy"], "platforms": [], "exclude_platforms": [], "max_hours": None, "prefer": {}}
    names = [r["game"]["title"] for r in ai.search_games(GAMES, intent, [], TODAY, 30)]
    assert names and not any("출시 예정" in n for n in names)


def test_find_game_fuzzy():
    assert ai.find_game(GAMES, "stardew valley")["title"] == "Stardew Valley"
    assert ai.find_game(GAMES, "Baldurs Gate 3")["title"] == "Baldur's Gate 3"
    assert ai.find_game(GAMES, "전혀없는게임이름xyz") is None


def test_prefer_cheap_and_indie():
    intent = {"genres": [], "tags": [], "platforms": [], "exclude_platforms": [], "max_hours": None,
              "prefer": {"cheap": True, "indie": True}}
    res = ai.search_games(GAMES, intent, [title("Elden Ring")], TODAY, 20)
    top = next(r for r in res if r["game"]["title"] == "Hades")
    assert "할인 중" in top["matched"]


# ---------- 추천 이유 ----------
def test_explain_validation():
    g = title("Stardew Valley")
    text, src = asyncio.run(ai.explain_game({}, g, "기본 문장", llm_returning({"text": "짧음"})))
    assert (text, src) == ("기본 문장", "rule")
    ok = "퇴근 후 짧게 쉬고 싶은 분께 [Stardew Valley]의 잔잔한 농장 생활을 추천해요."
    text, src = asyncio.run(ai.explain_game({}, g, "기본 문장", llm_returning({"text": ok})))
    assert src == "ollama" and text == ok


# ---------- 백로그 ----------
def _cands(*names):
    return [{"title": n, "genres": title(n)["genres"], "tags": title(n)["tags"],
             "playtime_hours": title(n)["playtime_hours"], "my_playtime_minutes": 0} for n in names]


def test_backlog_valid_pick_and_bad_index():
    c = _cands("Elden Ring", "Vampire Survivors", "Baldur's Gate 3")
    good = asyncio.run(ai.pick_backlog(c, "머리 비우고 싶어", 60, llm_returning({"pick": 1, "reason": "30분 단판으로 가볍게 스트레스를 풀기 좋아요."})))
    assert good["source"] == "ollama" and good["pick"]["title"] == "Vampire Survivors"
    for bad in ({"pick": 99, "reason": "충분히 긴 이유 문장입니다 정말로."}, {"pick": "1", "reason": "충분히 긴 이유 문장입니다 정말로."}, {"pick": True, "reason": "충분히 긴 이유 문장입니다 정말로."}):
        r = asyncio.run(ai.pick_backlog(c, "머리 비우고 싶어", 60, llm_returning(bad)))
        assert r["source"] == "rule" and r["pick"] in c


def test_backlog_rule_prefers_relaxing_for_short_time():
    c = _cands("Elden Ring", "Stardew Valley", "Baldur's Gate 3")
    r = asyncio.run(ai.pick_backlog(c, "머리 비우고 힐링", 60, llm_returning(RuntimeError("down"))))
    assert r["pick"]["title"] == "Stardew Valley"


# ---------- 플레이타임 계산기 ----------
def test_parse_availability():
    assert ai.parse_availability("주말에 하루 2시간씩 쓸 수 있어") == {"hours_per_day": 2.0, "days_per_week": 2.0}
    assert ai.parse_availability("주 6시간") == {"hours_per_day": 6.0, "days_per_week": 1.0}
    assert ai.parse_availability("매일 30분") == {"hours_per_day": 0.5, "days_per_week": 7.0}
    assert ai.parse_availability("시간 날 때") == {"hours_per_day": None, "days_per_week": None}


def test_schedule_math_matches_document_example():
    bg3 = ai.schedule_math(60, 2, 2, TODAY)  # 문서: 엔딩까지 약 15주
    assert bg3["weeks"] == 15.0 and bg3["weekly_hours"] == 4.0 and bg3["play_sessions"] == 30
    sanabi = ai.schedule_math(8, 2, 2, TODAY)  # 문서: 약 8시간, 4일 소요
    assert sanabi["play_sessions"] == 4 and sanabi["weeks"] == 2.0


def test_shorter_alternatives_and_message():
    bg3 = title("Baldur's Gate 3")
    alts = ai.shorter_alternatives(GAMES, bg3, 2)
    assert alts and all(a["game"]["playtime_hours"] < 30 for a in alts)
    plan = ai.schedule_math(60, 2, 2, TODAY)
    text, src = asyncio.run(ai.schedule_message(bg3, plan, alts, llm_returning(RuntimeError("down"))))
    assert src == "rule" and "15" in text and "[Baldur's Gate 3]" in text


# ---------- 리뷰 요약 ----------
def test_review_summary():
    reviews = ["전투가 정말 재미있어요", "후반부 최적화가 아쉬워요", "스토리와 연출이 훌륭합니다"]
    ok = {"pros": ["전투가 재미있다", "연출이 훌륭하다"], "cons": ["최적화 아쉬움"], "verdict": "전반적으로 호평"}
    out = asyncio.run(ai.summarize_reviews("X", reviews, llm_returning(ok)))
    assert out["pros"] and out["cons"] == ["최적화 아쉬움"] and out["review_count"] == 3
    for bad in ({"pros": [], "cons": [], "verdict": "x"}, {"pros": ["a"], "cons": []}, {"pros": "문자열", "verdict": "x"}):
        try:
            asyncio.run(ai.summarize_reviews("X", reviews, llm_returning(bad)))
        except ValueError:
            continue
        raise AssertionError("잘못된 LLM 출력은 ValueError 여야 함")
    try:
        asyncio.run(ai.summarize_reviews("X", reviews[:2], llm_returning(ok)))
    except ValueError:
        return
    raise AssertionError("리뷰 3개 미만은 거부해야 함")


# ---------- 할인 / 출시 예정 ----------
def test_rank_deals_prefers_matching_taste():
    cozy = ai.rank_deals(GAMES, [20, 60, 60, 60, 95, 10], TODAY)
    hard = ai.rank_deals(GAMES, [95, 40, 50, 50, 10, 70], TODAY)
    assert cozy["upcoming"] and cozy["upcoming"][0]["game"]["title"].startswith("(샘플) Cozy Garden")
    assert cozy["deals"][0]["game"]["title"] in ("Overcooked! 2", "Stardew Valley")
    assert hard["deals"][0]["game"]["title"] in ("Elden Ring", "Celeste", "Hades")
    assert all(d["discount_percent"] > 0 for d in cozy["deals"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
