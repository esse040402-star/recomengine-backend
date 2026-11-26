import asyncio
import re
import time
from datetime import datetime, timezone

import httpx

from app.config import get_settings

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API = "https://api.igdb.com/v4"
FIELDS = (
    "id,name,summary,first_release_date,cover.image_id,genres.name,themes.name,"
    "game_modes.name,player_perspectives.name,platforms.name,total_rating,url"
)

_token: dict = {"value": None, "expires_at": 0.0}
_lock = asyncio.Lock()


async def _get_token() -> str:
    async with _lock:
        if _token["value"] and time.time() < _token["expires_at"] - 60:
            return _token["value"]
        s = get_settings()
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                TOKEN_URL,
                params={
                    "client_id": s.igdb_client_id,
                    "client_secret": s.igdb_client_secret,
                    "grant_type": "client_credentials",
                },
            )
            r.raise_for_status()
            data = r.json()
        _token["value"] = data["access_token"]
        _token["expires_at"] = time.time() + int(data.get("expires_in", 3600))
        return _token["value"]


async def _query(body: str) -> list[dict]:
    s = get_settings()
    token = await _get_token()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{API}/games",
            content=body,
            headers={"Client-ID": s.igdb_client_id, "Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()


def _escape(text: str) -> str:
    return text.replace("\\", " ").replace('"', " ")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


async def search_many(name: str, limit: int = 10) -> list[dict]:
    return await _query(f'search "{_escape(name)}"; fields {FIELDS}; limit {limit};')


async def find_game(name: str) -> dict | None:
    """이름이 정확히 같은 결과를 우선, 없으면 첫 번째 결과를 돌려준다."""
    hits = await search_many(name, limit=5)
    if not hits:
        return None
    for h in hits:
        if _norm(h.get("name", "")) == _norm(name):
            return h
    return hits[0]


def to_game_row(g: dict) -> dict:
    image_id = (g.get("cover") or {}).get("image_id")
    ts = g.get("first_release_date")

    def names(key: str) -> list[str]:
        return [x["name"] for x in g.get(key, []) if isinstance(x, dict) and x.get("name")]

    return {
        "igdb_id": g["id"],
        "title": g["name"],
        "description": g.get("summary"),
        "release_date": datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if ts else None,
        "cover_url": f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg" if image_id else None,
        "genres": names("genres"),
        "tags": names("themes") + names("game_modes") + names("player_perspectives"),
        "platforms": names("platforms"),
        "source_data": {"igdb": {"rating": g.get("total_rating"), "url": g.get("url")}},
    }
