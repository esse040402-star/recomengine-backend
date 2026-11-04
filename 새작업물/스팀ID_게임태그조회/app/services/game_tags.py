"""스팀 앱 번호로 게임의 장르·태그를 찾아 RAWG/IGDB 이름으로 통일해서 돌려준다 (DB 에는 쓰지 않는다).
1순위: DB(games) 에 저장된 값 (RAWG/IGDB 수집 결과)
2순위: DB 에 없거나 비어 있으면 RAWG·IGDB 를 그때그때 조회 + 스팀 상점의 장르·카테고리를 합쳐서 통일
3순위: RAWG·IGDB 키가 없거나 둘 다 실패하면 스팀 상점 값만"""
import logging
import re

from app.config import get_settings
from app.db import get_supabase, run
from app.services import game_clean, igdb, market, rawg, safe_errors, steam

log = logging.getLogger(__name__)

COLUMNS = "id,title,steam_app_id,genres,tags"
TTL_LIVE = 6 * 3600   # 실시간 조회 결과를 서버 메모리에 보관하는 시간 (RAWG·IGDB 호출 한도 보호)
RAWG_CANDIDATES = 3   # 스팀 번호를 대조해 볼 RAWG 후보 수 (후보마다 호출 1번)


def _norm(name: str) -> str:
    """이름 비교용: 소문자 + 영숫자만 ('ELDEN RING' = 'Elden Ring', '™' 같은 기호 무시)."""
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


async def _rawg_row(title: str, app_id: int) -> dict | None:
    """RAWG 에서 같은 게임 찾기. 스팀 번호가 일치하는 후보를 우선하고, 없으면 이름이 정확히 같은 것만 쓴다."""
    hits = [h for h in await rawg.search(title, 5) if not game_clean.is_minor_rawg_entry(h)]
    ranked = sorted(hits, key=lambda h: _norm(h.get("name", "")) != _norm(title))
    for hit in ranked[:RAWG_CANDIDATES]:
        if await rawg.steam_app_id(hit["id"]) == app_id:
            return rawg.to_game_row(await rawg.detail(hit["id"]))
    for hit in ranked:
        if _norm(hit.get("name", "")) == _norm(title):
            return rawg.to_game_row(await rawg.detail(hit["id"]))
    return None


async def _igdb_row(title: str) -> dict | None:
    """IGDB 는 이름이 정확히 같은 결과만 쓴다 (다른 게임이 섞이지 않게)."""
    for hit in await igdb.search_many(title, 5):
        if _norm(hit.get("name", "")) == _norm(title):
            return igdb.to_game_row(hit)
    return None


async def _live(app_id: int, labels: dict) -> dict:
    """RAWG·IGDB·스팀 값을 모아 통일한다. 한 곳이 실패해도 나머지로 계속한다."""
    s = get_settings()
    title = labels["name"]
    genres, tags, used = list(labels["genres"]), list(labels["categories"]), []
    for name, enabled, fetch in (
        ("rawg", s.rawg_enabled, lambda: _rawg_row(title, app_id)),
        ("igdb", s.igdb_enabled, lambda: _igdb_row(title)),
    ):
        if not (enabled and title):
            continue
        try:
            row = await fetch()
        except Exception as exc:  # 이 서비스만 건너뛴다 (키가 로그에 새지 않게 종류만 남김)
            log.warning("%s 실시간 조회 실패(%s): %s", name.upper(), title, safe_errors.describe(exc))
            continue
        if row:
            genres += row["genres"]
            tags += row["tags"]
            used.append(name)
    genres, tags = game_clean.normalize(genres, tags)
    return {"title": title, "genres": genres, "tags": tags, "sources": used + ["steam"]}


async def tags_by_steam_app(app_id: int) -> dict | None:
    """-> {'steam_app_id', 'game_id', 'title', 'genres', 'tags', 'source', 'sources'}. 어디에도 없으면 None.
    source: 'db'(저장된 값) / 'live'(RAWG·IGDB 를 방금 조회) / 'steam'(스팀 값만).
    스팀 호출이 실패하면 예외가 그대로 올라간다 (라우터가 502 로 바꿈)."""
    res = await run(lambda: get_supabase().table("games").select(COLUMNS).eq("steam_app_id", app_id).limit(1).execute())
    row = res.data[0] if res.data else None
    if row:
        # 정리 전에 저장된 옛 데이터도 같은 규칙으로 다시 통일한다
        genres, tags = game_clean.normalize(row.get("genres"), row.get("tags"))
        if genres or tags:
            return {"steam_app_id": app_id, "game_id": row["id"], "title": row.get("title"),
                    "genres": genres, "tags": tags, "source": "db", "sources": ["db"]}

    labels = await steam.fetch_app_labels(app_id)
    if labels is None:
        return None
    entry = await market.cached(f"tags:{app_id}", TTL_LIVE, lambda: _live(app_id, labels))
    found = entry["data"]
    return {"steam_app_id": app_id, "game_id": row["id"] if row else None,
            "title": found["title"] or (row or {}).get("title"),
            "genres": found["genres"], "tags": found["tags"],
            "source": "steam" if found["sources"] == ["steam"] else "live", "sources": found["sources"]}
