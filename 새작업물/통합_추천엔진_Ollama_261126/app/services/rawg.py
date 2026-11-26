import httpx

from app.config import get_settings
from app.services.game_clean import steam_app_id_from_url

BASE = "https://api.rawg.io/api"


PLATFORM_IDS = {"pc": 4, "ps5": 187, "ps4": 18, "xbox": 1, "switch": 7, "ios": 3, "android": 21}


async def search(query: str, limit: int = 10, platform: str | None = None) -> list[dict]:
    s = get_settings()
    params = {"key": s.rawg_api_key, "search": query, "page_size": limit, "search_precise": "true"}
    if platform:
        params["platforms"] = PLATFORM_IDS[platform]
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{BASE}/games", params=params)
        r.raise_for_status()
        return r.json().get("results", [])


async def detail(rawg_id: int) -> dict:
    s = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{BASE}/games/{rawg_id}", params={"key": s.rawg_api_key})
        r.raise_for_status()
        return r.json()


STEAM_STORE_ID = 1


async def steam_app_id(rawg_id: int) -> int | None:
    """RAWG의 판매처 목록에서 스팀 상점 주소를 찾아 스팀 앱 id 를 꺼낸다 (리뷰 요약·가격 동기화에 필요).
    실패해도 게임 저장은 계속해야 하므로 None 을 돌려준다."""
    s = get_settings()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{BASE}/games/{rawg_id}/stores", params={"key": s.rawg_api_key})
            r.raise_for_status()
            stores = r.json().get("results", [])
    except Exception:
        return None
    for st in stores:
        app_id = steam_app_id_from_url(st.get("url"))
        if app_id and (st.get("store_id") in (None, STEAM_STORE_ID) or "steampowered" in (st.get("url") or "")):
            return app_id
    return None


def to_game_row(d: dict) -> dict:
    tags = [t["name"] for t in d.get("tags", []) if t.get("language") in (None, "eng")]
    platforms = [p["platform"]["name"] for p in d.get("platforms") or [] if p.get("platform")]
    return {
        "rawg_id": d["id"],
        "title": d["name"],
        "description": d.get("description_raw") or None,
        "release_date": d.get("released") or None,
        "cover_url": d.get("background_image"),
        "playtime_hours": d.get("playtime") or None,
        "genres": [g["name"] for g in d.get("genres", [])],
        "tags": tags[:40],
        "platforms": platforms,
        "source_data": {
            "rawg": {
                "rating": d.get("rating"),
                "metacritic": d.get("metacritic"),
                "ratings_count": d.get("ratings_count"),
                "esrb": (d.get("esrb_rating") or {}).get("name"),
                "website": d.get("website"),
            }
        },
    }
