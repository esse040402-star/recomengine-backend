"""스팀 랭킹·뉴스·리뷰·상세 API 통합 테스트 (가짜 스팀 응답, 네트워크 없음).  pytest 로 실행"""
import asyncio
import os

os.environ["USE_MOCK_DB"] = "true"

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import market, steam

calls = {}


def count(name):
    calls[name] = calls.get(name, 0) + 1


async def fake_most_played(limit=10):
    count("most_played")
    return [{"rank": 1, "app": 730}, {"rank": 2, "app": 570}]


async def fake_current_players(app_id):
    return None if app_id == 570 else 1234567


async def fake_store_names(app_ids):
    return {730: "Counter-Strike 2"}  # 570 은 이름이 없는 경우


def store_item(i, name, discounted=False, kind=0):
    return {"id": i, "type": kind, "name": name, "discounted": discounted, "discount_percent": 50 if discounted else 0,
            "original_price": 2000000, "final_price": 1000000 if discounted else 2000000, "currency": "KRW",
            "header_image": f"https://shared.akamai.steamstatic.com/{i}.jpg"}


async def fake_featured(cc="kr"):
    count("featured")
    return {
        "specials": {"items": [store_item(1, "세일 게임", True), store_item(2, "정가 게임", False), store_item(3, "DLC", True, kind=4)]},
        "new_releases": {"items": [store_item(10, "신작 게임"), store_item(11, "신작 DLC", kind=4)]},
    }


async def fake_news(app_id, n=3):
    count("news")
    return [{"id": f"g{app_id}", "title": f"{app_id} 업데이트", "url": "https://store.steampowered.com/news/x",
             "date": 1_790_000_000 + app_id % 1000, "source": "공지"}]


async def fake_summary(app_id):
    return {"positive": 90, "negative": 10, "total": 100, "description": "Very Positive"}


async def fake_review_page(app_id, sentiment="all", language="all", sort="recent", days="all", cursor="*", num=12):
    count("review_page")
    return {"items": [{"id": "1", "text": f"{sentiment}/{language}/{sort}/{days}", "truncated": False, "positive": True,
                       "created": 1, "updated": 1, "language": "koreana", "hours": 1.5, "helpful": 0,
                       "purchased": True, "receivedFree": False, "url": ""}],
            "cursor": None if cursor == "END" else "NEXT"}


async def fake_details(app_id, cc="kr"):
    return None if app_id == 620 else {"developers": ["Valve"], "korean": True, "price": {"price": 0, "originalPrice": 0, "discount": 0, "currency": "KRW"}}


@pytest.fixture()
def client(monkeypatch):
    for name, fn in {"fetch_most_played": fake_most_played, "fetch_current_players": fake_current_players,
                     "fetch_store_names": fake_store_names, "fetch_featured": fake_featured, "fetch_news": fake_news,
                     "fetch_review_summary": fake_summary, "fetch_review_page": fake_review_page,
                     "fetch_app_details": fake_details}.items():
        monkeypatch.setattr(steam, name, fn)
    market.clear_cache()
    calls.clear()
    with TestClient(app) as c:
        yield c
    market.clear_cache()


def test_status_feeds_on(client):
    assert client.get("/api/status").json()["feeds"] is True


def test_catalog_file_maps_prototype_ids():
    assert market.app_id_of("elden") == 1245620
    assert len(market.catalog()["news_games"]) == 12
    assert all(g in market.catalog()["games"] for g in market.catalog()["news_games"])


def test_rankings_shape_and_fallbacks(client):
    r = client.get("/api/market", params={"section": "rankings"}).json()
    assert r["section"] == "rankings" and r["updatedAt"]
    first, second = r["data"]
    assert first == {"rank": 1, "app": 730, "name": "Counter-Strike 2", "players": 1234567,
                     "url": "https://store.steampowered.com/app/730/"}
    assert second["players"] is None and second["name"]  # 접속자 수를 못 가져와도 줄은 남고, 이름이 없어도 대체 이름이 있다


def test_results_are_cached(client):
    client.get("/api/market", params={"section": "rankings"})
    client.get("/api/market", params={"section": "rankings"})
    assert calls["most_played"] == 1


def test_news_all_uses_representative_games(client):
    r = client.get("/api/market", params={"section": "news"}).json()
    d = r["data"]
    assert calls["news"] == 12  # 대표 게임 12개
    dates = [n["date"] for n in d["news"]]
    assert dates == sorted(dates, reverse=True)
    assert {"id", "game", "app", "title", "url", "date", "source"} <= set(d["news"][0])
    assert [s["title"] for s in d["sales"]] == ["세일 게임"]  # 할인 중인 '게임'만 (정가·DLC 제외)
    assert [s["title"] for s in d["newReleases"]] == ["신작 게임"]
    card = d["sales"][0]
    assert card == {"app": 1, "title": "세일 게임", "image": "https://shared.akamai.steamstatic.com/1.jpg",
                    "discount": 50, "price": 1000000, "originalPrice": 2000000, "currency": "KRW",
                    "url": "https://store.steampowered.com/app/1/"}


def test_news_for_one_game_still_returns_cards(client):
    d = client.get("/api/market", params={"section": "news", "game": "portal"}).json()["data"]
    assert calls["news"] == 1 and {n["game"] for n in d["news"]} == {"portal"}
    assert d["sales"] and d["newReleases"]  # 프론트가 이 값으로 기존 카드를 덮어쓰기 때문에 항상 있어야 한다


def test_news_survives_partial_failure(client, monkeypatch):
    async def flaky(app_id, n=3):
        if app_id == 620:
            raise httpx.ConnectError("x")
        return await fake_news(app_id, n)

    monkeypatch.setattr(steam, "fetch_news", flaky)
    r = client.get("/api/market", params={"section": "news"})
    assert r.status_code == 200 and r.json()["data"]["news"]


def test_review_summary_section(client):
    r = client.get("/api/market", params={"section": "reviews", "game": "elden"}).json()
    assert r["section"] == "reviews"
    assert r["data"] == {"positive": 90, "negative": 10, "total": 100, "description": "Very Positive",
                         "url": "https://store.steampowered.com/app/1245620/#app_reviews_hash"}
    miss = client.get("/api/market", params={"section": "reviews"})
    assert miss.status_code == 422 and "game" in miss.json()["error"]


def test_market_input_errors(client):
    assert client.get("/api/market", params={"section": "weird"}).status_code == 422
    unknown = client.get("/api/market", params={"section": "news", "game": "no-such-game"})
    assert unknown.status_code == 404 and isinstance(unknown.json()["error"], str)


def test_steam_reviews_passes_filters_and_cursor(client):
    r = client.get("/api/steam/reviews", params={"game": "elden", "sentiment": "positive", "days": "30",
                                                  "language": "koreana", "sort": "helpful", "cursor": "*"}).json()
    assert r["items"][0]["text"] == "positive/koreana/helpful/30"
    assert r["cursor"] == "NEXT" and r["checkedAt"]
    assert client.get("/api/steam/reviews", params={"game": "elden", "cursor": "END"}).json()["cursor"] is None
    assert client.get("/api/steam/reviews", params={"game": "elden", "sentiment": "bad"}).status_code == 422
    assert client.get("/api/steam/reviews", params={"game": "no-such-game"}).status_code == 404


def test_steam_details(client):
    r = client.get("/api/steam/details", params={"game": "elden"}).json()
    assert r["details"]["developers"] == ["Valve"] and r["details"]["price"]["price"] == 0
    assert client.get("/api/steam/details", params={"game": "portal"}).status_code == 404  # 스팀이 못 찾음 (가짜: 620)


def test_steam_failure_is_502_and_hides_key(client, monkeypatch):
    request = httpx.Request("GET", "https://store.steampowered.com/x?key=SECRETKEY123")

    async def boom(app_id):
        raise httpx.HTTPStatusError("bad https://store.steampowered.com/x?key=SECRETKEY123", request=request,
                                    response=httpx.Response(429, request=request))

    monkeypatch.setattr(steam, "fetch_review_summary", boom)
    r = client.get("/api/market", params={"section": "reviews", "game": "elden"})
    assert r.status_code == 502 and "429" in r.json()["error"]
    assert "SECRETKEY123" not in r.text


# ---------------------------------------------------------------- 순수 변환 로직
def test_parse_requirements():
    raw = ('<strong>최소:</strong><br><ul class="bb_ul"><li>64비트 프로세서와 운영 체제가 필요합니다<br></li>'
           '<li><strong>운영 체제:</strong> Windows&nbsp;10<br></li><li><strong>메모리:</strong> 12 GB RAM<br></li></ul>')
    assert steam.parse_requirements(raw) == [["안내", "64비트 프로세서와 운영 체제가 필요합니다"],
                                            ["운영 체제", "Windows 10"], ["메모리", "12 GB RAM"]]
    assert steam.parse_requirements(None) == []


def test_review_page_converts_and_filters_by_days(monkeypatch):
    import time

    now = int(time.time())
    raw = {"reviews": [
        {"recommendationid": 1, "review": "최근 리뷰", "timestamp_created": now - 86400, "voted_up": True,
         "votes_up": 4, "steam_purchase": True, "received_for_free": False, "language": "koreana",
         "author": {"steamid": "7656", "playtime_forever": 90}},
        {"recommendationid": 2, "review": "x" * 700, "timestamp_created": now - 100 * 86400, "voted_up": False,
         "author": {}},
    ], "cursor": "C2"}

    async def fake_get(url, params, timeout=15):
        fake_get.params = params
        return raw

    monkeypatch.setattr(steam, "_get_json", fake_get)
    page = asyncio.run(steam.fetch_review_page(1, days="30", sort="recent"))
    assert [i["id"] for i in page["items"]] == ["1"] and page["cursor"] == "C2"  # 최신순은 기간을 직접 거른다
    assert "day_range" not in fake_get.params and fake_get.params["filter"] == "recent"
    item = page["items"][0]
    assert item["hours"] == 1.5 and item["helpful"] == 4 and item["url"].endswith("/profiles/7656/recommended/1/")
    helpful = asyncio.run(steam.fetch_review_page(1, days="30", sort="helpful"))
    assert fake_get.params["day_range"] == 30 and fake_get.params["filter"] == "all"
    assert [i["truncated"] for i in helpful["items"]] == [False, True]  # 도움순은 스팀이 기간을 처리하므로 직접 거르지 않는다
    assert len(helpful["items"][1]["text"]) == steam.REVIEW_TEXT_MAX
