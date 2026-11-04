"""스팀 앱 번호로 장르·태그 조회 API 테스트 (가짜 DB + 가짜 스팀·RAWG·IGDB 응답, 네트워크 없음).  pytest 로 실행"""
import os

os.environ["USE_MOCK_DB"] = "true"

from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import game_clean, game_tags, igdb, market, rawg, steam

ELDEN = 1245620  # mock_games.json 에 steam_app_id 가 들어 있는 게임
NEW_GAME = 999   # DB 에 없는 게임
calls = {}


def count(name):
    calls[name] = calls.get(name, 0) + 1


async def fake_labels(app_id):
    if app_id == NEW_GAME:
        return {"name": "NEW GAME™", "genres": ["Action", "Role-playing (RPG)"],
                "categories": ["Single-player", "Multi-player", "Co-op", "Steam Achievements", "Full controller support"]}
    return None  # 스팀도 모르는 번호


async def fake_rawg_search(query, limit=10, platform=None):
    count("rawg_search")
    big = {"ratings_count": 500, "added": 5000}
    return [{"id": 1, "name": "New Game Remastered", **big},   # 이름이 비슷하지만 다른 게임
            {"id": 2, "name": "New Game", **big},
            {"id": 3, "name": "New Game Fan Mod", "ratings_count": 0, "added": 0}]  # 비공식 항목


async def fake_rawg_steam_id(rawg_id):
    return {1: 111, 2: NEW_GAME}.get(rawg_id)


async def fake_rawg_detail(rawg_id):
    count(f"rawg_detail_{rawg_id}")
    return {"id": rawg_id, "name": "New Game", "genres": [{"name": "Action"}, {"name": "Platformer"}],
            "tags": [{"name": "Open World", "language": "eng"}, {"name": "Steam Achievements", "language": "eng"},
                     {"name": "Atmospheric", "language": "eng"}, {"name": "열린 세계", "language": "kor"}],
            "platforms": []}


async def fake_igdb_search(name, limit=10):
    count("igdb_search")
    return [{"id": 7, "name": "New Game 2"},
            {"id": 8, "name": "new game", "genres": [{"name": "Platform"}, {"name": "Role-playing (RPG)"}],
             "themes": [{"name": "Science fiction"}], "game_modes": [{"name": "Co-operative"}],
             "player_perspectives": [{"name": "Side view"}]}]


def settings(rawg_on=False, igdb_on=False):
    return lambda: SimpleNamespace(rawg_enabled=rawg_on, igdb_enabled=igdb_on)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(steam, "fetch_app_labels", fake_labels)
    monkeypatch.setattr(game_tags, "get_settings", settings())  # 기본: RAWG·IGDB 키 없음 (실제 호출 방지)
    monkeypatch.setattr(rawg, "search", fake_rawg_search)
    monkeypatch.setattr(rawg, "steam_app_id", fake_rawg_steam_id)
    monkeypatch.setattr(rawg, "detail", fake_rawg_detail)
    monkeypatch.setattr(igdb, "search_many", fake_igdb_search)
    market.clear_cache()
    calls.clear()
    with TestClient(app) as c:
        yield c


def test_known_game_returns_db_tags(client):
    r = client.get(f"/api/games/by-steam/{ELDEN}")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "db" and body["sources"] == ["db"]
    assert body["steam_app_id"] == ELDEN and body["title"] == "Elden Ring" and body["game_id"]
    assert body["genres"] == ["Action", "RPG"]
    assert {"Open World", "Singleplayer", "Co-op"} <= set(body["tags"])
    assert not calls  # DB 에 있으면 RAWG·IGDB 를 부르지 않는다


def test_without_rawg_igdb_keys_uses_steam_only(client):
    r = client.get(f"/api/games/by-steam/{NEW_GAME}")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "steam" and body["sources"] == ["steam"] and body["game_id"] is None
    assert body["title"] == "NEW GAME™"
    assert body["genres"] == ["Action", "RPG"]                                  # Role-playing (RPG) -> RPG
    assert body["tags"] == ["Singleplayer", "Multiplayer", "Co-op"]             # Single-player 등 통일, 기능 표시 제거
    assert not calls


def test_live_lookup_merges_rawg_igdb_steam_with_unified_names(client, monkeypatch):
    monkeypatch.setattr(game_tags, "get_settings", settings(rawg_on=True, igdb_on=True))
    r = client.get(f"/api/games/by-steam/{NEW_GAME}")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "live" and body["sources"] == ["rawg", "igdb", "steam"]
    assert body["genres"] == ["Action", "RPG", "Platformer"]                    # Platform(IGDB) = Platformer(RAWG)
    assert body["tags"] == ["Singleplayer", "Multiplayer", "Co-op", "Open World", "Atmospheric", "Sci-fi", "2D"]
    assert "Steam Achievements" not in body["tags"] and "열린 세계" not in body["tags"]
    assert calls["rawg_detail_2"] == 1 and "rawg_detail_1" not in calls         # 스팀 번호가 같은 후보만 사용


def test_live_result_is_cached(client, monkeypatch):
    monkeypatch.setattr(game_tags, "get_settings", settings(rawg_on=True, igdb_on=True))
    for _ in range(3):
        assert client.get(f"/api/games/by-steam/{NEW_GAME}").status_code == 200
    assert calls["rawg_search"] == 1 and calls["igdb_search"] == 1


def test_live_lookup_survives_one_service_failing(client, monkeypatch):
    monkeypatch.setattr(game_tags, "get_settings", settings(rawg_on=True, igdb_on=True))

    async def boom(*args, **kwargs):
        req = httpx.Request("GET", "https://api.rawg.io/api/games?key=SECRET123")
        raise httpx.HTTPStatusError("fail", request=req, response=httpx.Response(500, request=req))

    monkeypatch.setattr(rawg, "search", boom)
    r = client.get(f"/api/games/by-steam/{NEW_GAME}")
    assert r.status_code == 200
    body = r.json()
    assert body["sources"] == ["igdb", "steam"] and "Sci-fi" in body["tags"]
    assert "SECRET123" not in r.text


def test_name_must_match_exactly_when_steam_id_is_unknown(client, monkeypatch):
    """스팀 번호로 대조할 수 없어도, 이름이 정확히 같은 게임이 아니면 RAWG 값을 쓰지 않는다."""
    monkeypatch.setattr(game_tags, "get_settings", settings(rawg_on=True))

    async def other_game_only(query, limit=10, platform=None):
        return [{"id": 1, "name": "New Game Remastered", "ratings_count": 500, "added": 5000}]

    monkeypatch.setattr(rawg, "search", other_game_only)
    body = client.get(f"/api/games/by-steam/{NEW_GAME}").json()
    assert body["source"] == "steam" and "Open World" not in body["tags"]


def test_game_nobody_knows_is_404(client):
    r = client.get("/api/games/by-steam/123456")
    assert r.status_code == 404 and "찾을 수 없" in r.json()["error"]


def test_bad_app_id_is_422(client):
    assert client.get("/api/games/by-steam/0").status_code == 422
    assert client.get("/api/games/by-steam/abc").status_code == 422


def test_steam_failure_is_502_and_hides_key(client, monkeypatch):
    async def boom(app_id):
        req = httpx.Request("GET", "https://store.steampowered.com/api/appdetails?key=SECRET123")
        raise httpx.HTTPStatusError("fail", request=req, response=httpx.Response(500, request=req))

    monkeypatch.setattr(steam, "fetch_app_labels", boom)
    r = client.get(f"/api/games/by-steam/{NEW_GAME}")
    assert r.status_code == 502
    assert "SECRET123" not in r.text


def test_empty_db_tags_use_live_lookup(client):
    """DB 에 게임은 있어도 장르·태그가 비어 있으면 스팀 값을 쓴다 (game_id 는 DB 값 유지)."""
    from app.db import get_supabase
    get_supabase().table("games").insert({"title": "빈 게임", "steam_app_id": NEW_GAME, "genres": [], "tags": []}).execute()
    body = client.get(f"/api/games/by-steam/{NEW_GAME}").json()
    assert body["source"] == "steam" and body["game_id"] and body["genres"] == ["Action", "RPG"]


def test_open_world_spelling_is_fixed_whichever_service_comes_first():
    assert game_clean.normalize([], ["Open world"])[1] == ["Open World"]   # IGDB 표기
    assert game_clean.normalize([], ["Open World"])[1] == ["Open World"]   # RAWG 표기


def test_steam_category_names_unify_with_rawg_igdb():
    genres, tags = game_clean.normalize(
        ["Action"], ["Single-player", "Multi-player", "Shared/Split Screen", "Stereo Sound", "Steam Input API", "Co-op"])
    assert genres == ["Action"]
    assert tags == ["Singleplayer", "Multiplayer", "Split Screen", "Co-op"]
