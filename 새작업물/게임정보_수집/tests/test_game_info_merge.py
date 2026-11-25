"""게임 정보 정리 규칙 테스트 (인터넷·키 불필요).
실행: python -m tests.test_game_info_merge   (pytest 로도 실행 가능)
아래 응답은 Steam/IGDB 응답 '형식'을 흉내 낸 예시이며 실제 값과 다를 수 있다."""
import csv
import io
import json
import tempfile
from pathlib import Path

from app.services import game_info_merge as m

STEAM_EN = {
    "type": "game", "name": "Example Quest", "is_free": False,
    "short_description": "An <b>action</b> RPG.",
    "about_the_game": "<h2>About</h2><p>Explore &amp; fight.</p>",
    "header_image": "https://shared.cdn.steamstatic.com/store_item_assets/steam/apps/1/header.jpg",
    "capsule_image": "https://shared.cdn.steamstatic.com/store_item_assets/steam/apps/1/capsule_231x87.jpg",
    "developers": ["Dev Studio"], "publishers": ["Big Pub", "Big Pub"],
    "platforms": {"windows": True, "mac": False, "linux": True},
    "genres": [{"id": "1", "description": "Action"}, {"id": "3", "description": "RPG"}],
    "categories": [{"id": 2, "description": "Single-player"}, {"id": 38, "description": "Online Co-op"}],
    "release_date": {"coming_soon": False, "date": "24 Feb, 2022"},
}
STEAM_KO = {**STEAM_EN, "name": "예시 퀘스트", "short_description": "액션 RPG입니다.",
            "about_the_game": "<p>탐험하고 싸우세요.</p>", "genres": [{"id": "1", "description": "액션"}]}
REVIEWS = {"total_positive": 900, "total_negative": 100, "total_reviews": 1000}
IGDB = {
    "id": 777, "name": "Example Quest", "url": "https://www.igdb.com/games/example-quest",
    "summary": "IGDB summary.", "storyline": "A long <i>story</i>.",
    "first_release_date": 1645660800,  # 2022-02-24
    "genres": [{"name": "Role-playing (RPG)"}, {"name": "Adventure"}],
    "themes": [{"name": "Fantasy"}, {"name": "Science fiction"}],
    "game_modes": [{"name": "Single player"}, {"name": "Co-operative"}],
    "multiplayer_modes": [{"offlinecoop": True, "onlinecoop": False, "splitscreen": True}],
    "player_perspectives": [{"name": "Third person"}],
    "keywords": [{"name": "open world"}, {"name": "soulslike"}],
    "platforms": [{"name": "PC (Microsoft Windows)"}, {"name": "PlayStation 5"}, {"name": "Android"}, {"name": "iOS"}],
    "cover": {"image_id": "co123"}, "artworks": [{"image_id": "ar9"}],
    "involved_companies": [{"company": {"name": "Dev Studio"}, "developer": True, "publisher": False},
                           {"company": {"name": "Big Pub"}, "developer": False, "publisher": True}],
}


def full():
    return m.build_record(1, STEAM_EN, STEAM_KO, REVIEWS, IGDB, "example")


def test_ids_and_names():
    r = full()
    assert (r["steam_app_id"], r["igdb_id"], r["catalog_key"]) == (1, 777, "example")
    assert (r["steam_name"], r["steam_name_ko"], r["igdb_name"]) == ("Example Quest", "예시 퀘스트", "Example Quest")


def test_images():
    r = full()
    assert r["steam_header_image"].endswith("header.jpg") and r["steam_capsule_image"].endswith("capsule_231x87.jpg")
    assert r["igdb_cover_image"] == "https://images.igdb.com/igdb/image/upload/t_cover_big/co123.jpg"
    assert r["igdb_artwork_image"].endswith("/t_1080p/ar9.jpg")


def test_descriptions():
    r = full()
    assert r["steam_short_description"] == "액션 RPG입니다." and r["steam_description"] == "탐험하고 싸우세요."
    assert r["igdb_summary"] == "IGDB summary." and r["igdb_storyline"] == "A long story."


def test_labels_kept_as_original_per_source():
    """이름 통일 없음: 원래 표현 그대로, 출처별 칸에."""
    r = full()
    assert r["steam_genres"] == ["Action", "RPG"]           # 영어 응답 기준
    assert r["igdb_genres"] == ["Role-playing (RPG)", "Adventure"]
    assert r["igdb_themes"] == ["Fantasy", "Science fiction"]
    assert r["igdb_keywords"] == ["open world", "soulslike"]
    assert r["igdb_player_perspectives"] == ["Third person"]
    assert r["steam_categories"] == ["Single-player", "Online Co-op"]
    assert r["igdb_game_modes"] == ["Single player", "Co-operative"]
    assert r["igdb_multiplayer_modes"] == ["offlinecoop", "splitscreen"]


def test_platforms_exclude_mobile():
    r = full()
    assert r["steam_platforms"] == ["windows", "linux"]
    assert r["igdb_platforms"] == ["PC (Microsoft Windows)", "PlayStation 5"]
    assert r["excluded_mobile_platforms"] == ["Android", "iOS"]


def test_dates_companies_reviews_free():
    r = full()
    assert r["steam_release_date"] == "2022-02-24" and r["igdb_first_release_date"] == "2022-02-24"
    assert r["steam_developers"] == ["Dev Studio"] and r["steam_publishers"] == ["Big Pub"]
    assert r["igdb_developers"] == ["Dev Studio"] and r["igdb_publishers"] == ["Big Pub"]
    assert (r["steam_positive"], r["steam_negative"], r["steam_review_total"]) == (900, 100, 1000)
    assert r["steam_is_free"] is False


def test_steam_only_and_igdb_only():
    s = m.build_record(1, STEAM_EN, STEAM_KO, REVIEWS, None)
    assert s["igdb_id"] is None and s["igdb_genres"] == [] and s["igdb_cover_image"] is None
    i = m.build_record(5, None, None, None, IGDB)
    assert i["steam_name"] is None and i["igdb_name"] == "Example Quest"
    assert i["steam_positive"] is None and i["steam_is_free"] is None


def test_image_only_korean_description_falls_back_to_english():
    ko = {**STEAM_KO, "about_the_game": '<img src="https://x/a.gif"><br><img src="https://x/b.gif">'}
    r = m.build_record(1, STEAM_EN, ko, REVIEWS, None)
    assert r["steam_description"] == "About\nExplore & fight."


def test_release_date_formats():
    assert m.steam_release_date("Feb 24, 2022") == "2022-02-24"
    assert m.steam_release_date("24 Feb, 2022") == "2022-02-24"
    assert m.steam_release_date("Coming soon") is None
    assert m.steam_release_date("Q1 2026") is None


def test_pick_igdb_match_among_steam_linked():
    cands = [{"id": 50, "name": "Example Quest Deluxe"}, {"id": 70, "name": "Example Quest™"}, {"id": 10, "name": "Other"}]
    assert m.pick_igdb_match(cands, "Example Quest")["id"] == 70
    assert m.pick_igdb_match(cands, "Unknown")["id"] == 10
    assert m.pick_igdb_match([], "x") is None


def test_csv_row():
    row = m.to_csv_row(full())
    assert list(row) == m.CSV_COLUMNS
    assert row["igdb_genres"] == "Role-playing (RPG) | Adventure"
    assert row["steam_is_free"] == "FALSE" and row["steam_name_ko"] == "예시 퀘스트"


def test_collect_script_end_to_end_offline():
    """수집 스크립트를 인터넷 없이 끝까지 실행 (HTTP 함수만 가짜로 바꿈)."""
    import scripts.collect_game_info as c

    calls = []

    def fake_http(url, params=None, data=None, headers=None, timeout=20):
        calls.append((url, data.decode() if data else ""))
        if url.endswith("/oauth2/token"):
            return {"access_token": "t", "expires_in": 3600}
        if url.endswith("/api/appdetails"):
            d = STEAM_EN if params["l"] == "english" else STEAM_KO
            return {str(params["appids"]): {"success": params["appids"] in (1, 3), "data": {**d, "name": f"G{params['appids']}"}}}
        if "/IUserReviewsService/GetAppReviews/" in url:
            req = json.loads(params["input_json"])
            assert req["languages"] == ["all"] and req["appid"] in (1, 3)
            return {"response": {"success": 1, "query_summary": REVIEWS, "reviews": []}}
        if url.endswith("/external_games"):
            return [{"game": 777, "uid": "1", "external_game_source": 1},
                    {"game": 999, "uid": "1", "external_game_source": 5}]  # 다른 상점 번호는 무시
        if url.endswith("/games"):
            return [IGDB] if "where id" in data.decode() else []
        raise AssertionError(url)

    old = (c.http_json, c.STEAM_DELAY, c.IGDB_DELAY, c.load_env)
    c.http_json, c.STEAM_DELAY, c.IGDB_DELAY = fake_http, 0, 0
    c.load_env = lambda path: {"IGDB_CLIENT_ID": "x", "IGDB_CLIENT_SECRET": "y"}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            c.main(["--apps", "1,2,3", "--out", tmp])
            data = json.loads((Path(tmp) / "games.json").read_text(encoding="utf-8"))
            assert data["meta"]["count"] == 2
            g1, g3 = data["games"]
            assert g1["igdb_id"] == 777
            assert g3["igdb_id"] is None  # Steam 연결이 없으면 이름이 비슷해도 붙이지 않음
            assert not any("search" in body for _, body in calls)  # 이름 검색을 하지 않음
            rows = list(csv.DictReader(io.StringIO((Path(tmp) / "games.csv").read_text(encoding="utf-8-sig"))))
            assert rows[0]["steam_name"] == "G1"
            report = json.loads((Path(tmp) / "collect_report.json").read_text(encoding="utf-8"))
            assert report["failed"][0]["steam_app_id"] == 2
            assert g1["steam_positive"] == 900
            assert report["igdb_not_linked"] == [{"steam_app_id": 3, "name": "G3"}]
            c.http_json = lambda *a, **k: (_ for _ in ()).throw(AssertionError("캐시를 안 씀"))
            c.main(["--apps", "1,3", "--out", tmp])  # 두 번째 실행은 캐시만 사용
    finally:
        c.http_json, c.STEAM_DELAY, c.IGDB_DELAY, c.load_env = old





def test_reviews_html_response_does_not_drop_game():
    """리뷰 API가 JSON 대신 HTML을 주면 리뷰 칸만 비우고 게임 정보는 저장한다."""
    import scripts.collect_game_info as c

    def fake_http(url, params=None, data=None, headers=None, timeout=20):
        if url.endswith("/api/appdetails"):
            return {str(params["appids"]): {"success": True, "data": STEAM_EN}}
        raise c.HttpError(-1, "JSON 이 아닌 응답")

    old = (c.http_json, c.STEAM_DELAY)
    c.http_json, c.STEAM_DELAY = fake_http, 0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            c.main(["--apps", "1", "--out", tmp, "--no-igdb"])
            g = json.loads((Path(tmp) / "games.json").read_text(encoding="utf-8"))["games"][0]
            assert g["steam_name"] == "Example Quest" and g["steam_positive"] is None
    finally:
        c.http_json, c.STEAM_DELAY = old

def test_popular_games_from_steamspy_and_non_game_excluded():
    """--top: SteamSpy 전체 목록에서 리뷰 많은 순. --top-per-genre: 같은 후보를 IGDB 장르로 나눠 고름. DLC 등은 제외."""
    import argparse
    import scripts.collect_game_info as c

    spy_calls = []
    spy_all = {"10": {"positive": 50, "negative": 5}, "20": {"positive": 900, "negative": 100},
               "30": {"positive": 300, "negative": 0}, "40": {"positive": 1, "negative": 0},
               "50": {"positive": 800, "negative": 1}}
    igdb_genres = {"10": "Puzzle", "20": "Shooter", "30": "Role-playing (RPG)", "50": "Role-playing (RPG)"}

    def fake_http(url, params=None, data=None, headers=None, timeout=20):
        body = data.decode() if data else ""
        if url == c.STEAMSPY:
            spy_calls.append(dict(params))
            assert params["request"] == "all"  # 고장 난 genre/tag 요청은 쓰지 않음
            return spy_all
        if url.endswith("/oauth2/token"):
            return {"access_token": "t"}
        if url.endswith("/external_games"):
            return [{"game": int(a) * 10, "uid": a, "external_game_source": 1} for a in igdb_genres]
        if url.endswith("/games"):
            return [{"id": int(a) * 10, "genres": [{"name": g}]} for a, g in igdb_genres.items()
                    if str(int(a) * 10) in body]
        if url.endswith("/api/appdetails"):
            app = params["appids"]
            assert params["l"] == "english"  # --no-korean
            return {str(app): {"success": True, "data": {**STEAM_EN, "name": f"G{app}",
                                                          "type": "dlc" if app == 30 else "game"}}}
        if "/GetAppReviews/" in url:
            assert json.loads(params["input_json"])["appid"] != 30  # 게임 아닌 앱은 리뷰를 묻지 않음
            return {"response": {"query_summary": REVIEWS}}
        raise AssertionError(url)

    old = (c.http_json, c.STEAM_DELAY, c.STEAMSPY_DELAY, c.IGDB_DELAY, c.load_env, c.GENRE_POOL_PAGES)
    c.http_json, c.STEAM_DELAY, c.STEAMSPY_DELAY, c.IGDB_DELAY, c.GENRE_POOL_PAGES = fake_http, 0, 0, 0, 1
    c.load_env = lambda path: {"IGDB_CLIENT_ID": "x", "IGDB_CLIENT_SECRET": "y"}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cache = c.Cache(Path(tmp) / ".cache", False)
            args = argparse.Namespace(apps="99", no_catalog=False, top=2, top_per_genre=1,
                                      genres="Role-playing (RPG),Puzzle", min_reviews=10, limit=0, pool_pages=0)
            # top 2 = 20, 50 / RPG 1위 = 50(중복) / Puzzle 1위 = 10
            assert c.load_targets(args, cache) == [(99, None), (20, None), (50, None), (10, None)]
            c.main(["--apps", "99,30", "--top", "2", "--no-korean", "--no-igdb", "--out", tmp])
            data = json.loads((Path(tmp) / "games.json").read_text(encoding="utf-8"))
            assert [g["steam_app_id"] for g in data["games"]] == [99, 20, 50]
            assert data["games"][0]["steam_name_ko"] is None
            report = json.loads((Path(tmp) / "collect_report.json").read_text(encoding="utf-8"))
            assert report["not_a_game_excluded"] == [{"steam_app_id": 30, "name": "G30", "type": "dlc"}]
            assert len(spy_calls) == 1  # 두 번째부터는 SteamSpy 캐시 사용
    finally:
        c.http_json, c.STEAM_DELAY, c.STEAMSPY_DELAY, c.IGDB_DELAY, c.load_env, c.GENRE_POOL_PAGES = old


def test_steamspy_empty_response_is_error_and_not_cached():
    import scripts.collect_game_info as c
    old = (c.http_json, c.STEAMSPY_DELAY)
    c.http_json, c.STEAMSPY_DELAY = (lambda *a, **k: {}), 0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cache = c.Cache(Path(tmp) / ".cache", False)
            try:
                c.steamspy_list({"request": "all", "page": 0}, cache)
                raise AssertionError("빈 목록인데 오류가 안 남")
            except c.HttpError:
                pass
            assert not list((Path(tmp) / ".cache").glob("steamspy_*"))
    finally:
        c.http_json, c.STEAMSPY_DELAY = old

def test_steamspy_bad_page_is_retried_then_skipped():
    """SteamSpy 한 페이지가 오류 페이지(HTML)를 주면 한 번 더 시도하고, 그래도 안 되면 건너뛰고 계속한다."""
    import scripts.collect_game_info as c
    calls = []

    def fake_http(url, params=None, **k):
        calls.append(params["page"])
        if params["page"] == 1:
            raise c.HttpError(-1, "JSON 이 아닌 응답")
        return {str(100 + params["page"]): {"positive": 10, "negative": 0}}

    old = (c.http_json, c.STEAMSPY_DELAY)
    c.http_json, c.STEAMSPY_DELAY = fake_http, 0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            rows = c.steamspy_pool(3, c.Cache(Path(tmp) / ".cache", False))
            assert sorted(rows) == ["100", "102"] and calls == [0, 1, 1, 2]
    finally:
        c.http_json, c.STEAMSPY_DELAY = old



if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)} passed")
