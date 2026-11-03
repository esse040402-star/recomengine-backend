"""게임 데이터 정리 / 키 노출 방지 / 1000행 페이지 읽기 테스트 (fastapi·네트워크 불필요).
python -m tests.test_game_clean"""
from types import SimpleNamespace

from app.mock_db import MockSupabase
from app.services import game_clean, safe_errors
from app.services.paging import collect_pages
from app.services.recommender import recommend

# 실제 Hollow Knight 응답(스크린샷)에 있던 값
REAL_GENRES = ["Action", "Indie", "Platformer", "Platform", "Adventure"]
REAL_TAGS = ["Singleplayer", "Steam Achievements", "Full controller support", "Steam Cloud", "Atmospheric",
             "steam-trading-cards", "Great Soundtrack", "Story Rich", "Open World", "2D", "Exploration", "Difficult", "Controller"]


def test_real_hollow_knight_is_cleaned():
    genres, tags = game_clean.normalize(REAL_GENRES, REAL_TAGS)
    assert genres == ["Action", "Indie", "Platformer", "Adventure"]          # Platform(IGDB) = Platformer(RAWG)
    for noise in ("Steam Achievements", "Full controller support", "Steam Cloud", "steam-trading-cards", "Controller"):
        assert noise not in tags
    assert tags == ["Singleplayer", "Atmospheric", "Great Soundtrack", "Story Rich", "Open World", "2D", "Exploration", "Difficult"]


def test_igdb_names_are_unified():
    genres, tags = game_clean.normalize(
        ["Role-playing (RPG)", "Turn-based strategy (TBS)", "Real Time Strategy (RTS)", "Hack and slash/Beat 'em up"],
        ["Single player", "Co-operative", "Action", "Science fiction", "Side view", "Text", "Erotic", "co-op"],
    )
    assert genres == ["RPG", "Strategy", "Action"]
    assert tags == ["Singleplayer", "Co-op", "Sci-fi", "2D", "Sexual Content", "Turn-Based", "RTS", "Hack and Slash"]
    # 'Action' 은 장르와 같아서 태그에서 빠지고, 'co-op' 중복도 빠진다. 'Text'(시점) 는 버림


def test_clean_row_keeps_other_fields_and_caps_tags():
    row = {"title": "X", "rawg_id": 1, "genres": ["Platform"], "tags": [f"T{i}" for i in range(60)]}
    out = game_clean.clean_row(row)
    assert out["title"] == "X" and out["rawg_id"] == 1 and out["genres"] == ["Platformer"]
    assert len(out["tags"]) == game_clean.MAX_TAGS and row["genres"] == ["Platform"]  # 원본은 그대로


def test_minor_rawg_entries():
    junk = {"name": "Hollow Knight-Scene Design", "ratings_count": 0, "added": 3, "metacritic": None}
    assert game_clean.is_minor_rawg_entry(junk)
    assert not game_clean.is_minor_rawg_entry({"ratings_count": 3000, "added": 9000, "metacritic": 87})
    assert not game_clean.is_minor_rawg_entry({"ratings_count": 0, "added": 400})   # 출시 전이지만 관심 많은 게임
    assert not game_clean.is_minor_rawg_entry({"ratings_count": 0, "added": 0, "metacritic": 75})


def test_steam_app_id_from_url():
    assert game_clean.steam_app_id_from_url("https://store.steampowered.com/app/367520/Hollow_Knight/") == 367520
    assert game_clean.steam_app_id_from_url("https://www.gog.com/game/hollow_knight") is None
    assert game_clean.steam_app_id_from_url(None) is None


def test_errors_never_contain_api_keys():
    url = "https://api.rawg.io/api/games?key=SECRET123&search=x"
    exc = Exception(f"Client error '401 Unauthorized' for url '{url}'")
    exc.response = SimpleNamespace(status_code=401)
    for text in (safe_errors.describe(exc), safe_errors.status_hint(exc)):
        assert "SECRET123" not in text and "key=" not in text
    assert safe_errors.describe(exc) == "Exception(status=401)" and "401" in safe_errors.status_hint(exc)
    assert "연결" in safe_errors.status_hint(ConnectionError(url))
    assert "429" in safe_errors.status_hint(SimpleNamespace(response=SimpleNamespace(status_code=429)))


def test_collect_pages_reads_past_page_limit():
    db = MockSupabase(seed=False)
    db.table("games").insert([{"title": f"G{i:02d}"} for i in range(7)]).execute()
    calls = []

    def fetch(start, end):
        calls.append((start, end))
        return db.table("games").select("id,title").order("id").range(start, end).execute().data

    rows = collect_pages(fetch, page_size=3)
    assert len(rows) == 7 and len({r["id"] for r in rows}) == 7      # 빠지거나 겹친 행 없음
    assert calls == [(0, 2), (3, 5), (6, 8)]
    assert len(collect_pages(fetch, page_size=3, max_rows=4)) == 4   # 상한
    assert collect_pages(lambda s, e: [], page_size=3) == []


def test_in_app_purchases_counts_as_monetization():
    games = MockSupabase().table("games").select("*").execute().data
    stardew = next(g for g in games if g["title"] == "Stardew Valley")
    gacha = {**stardew, "id": "iap", "title": "IAP Sample", "tags": stardew["tags"] + ["In-App Purchases"]}
    ids = [r["game_id"] for r in recommend([40, 50, 50, 50, 80, 20], games + [gacha], {"avoid": ["monetization"]}, limit=40)]
    assert "iap" not in ids and stardew["id"] in ids


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
