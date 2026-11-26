"""스팀 랭킹·뉴스·할인·리뷰·상세를 프론트(/api/market, /api/steam/*)가 기대하는 모양으로 만든다.
DB에는 쓰지 않고, 스팀을 자주 부르지 않도록 메모리에 잠깐 보관(캐시)한다.
스팀 호출 함수는 steam 모듈의 것을 그대로 쓰므로 테스트에서는 steam.fetch_* 를 가짜로 바꿔 끼우면 된다."""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from app.services import safe_errors, steam

log = logging.getLogger("market")

CATALOG_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "catalog_apps.json"

RANK_COUNT = 10
NEWS_PER_GAME = 4
CARD_COUNT = 4  # 신작·할인 카드 수
NEWS_CONCURRENCY = 6

# 캐시 보관 시간(초)
TTL_RANKINGS = 10 * 60
TTL_NEWS = 30 * 60
TTL_FEATURED = 30 * 60
TTL_SUMMARY = 30 * 60
TTL_REVIEWS = 5 * 60
TTL_DETAILS = 60 * 60
MAX_CACHE_ENTRIES = 600


# ---------------------------------------------------------------- 게임 id <-> 스팀 앱 번호
@lru_cache(maxsize=1)
def catalog() -> dict:
    """data/catalog_apps.json (python -m scripts.export_catalog 로 만든다). 없으면 빈 표."""
    try:
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("data/catalog_apps.json 이 없거나 읽을 수 없습니다. python -m scripts.export_catalog 로 만드세요.")
        return {"news_games": [], "games": {}}
    return {"news_games": data.get("news_games", []), "games": data.get("games", {})}


def app_id_of(game: str) -> int:
    """프론트 게임 id -> 스팀 앱 번호. 모르는 id 면 LookupError."""
    entry = catalog()["games"].get(game)
    if not entry:
        raise LookupError(game)
    return int(entry["app"])


def title_of_app(app: int) -> str | None:
    for entry in catalog()["games"].values():
        if entry.get("app") == app:
            return entry.get("title")
    return None


# ---------------------------------------------------------------- 캐시
_cache: dict[str, tuple[float, dict]] = {}
_locks: dict[str, asyncio.Lock] = {}


def clear_cache() -> None:
    _cache.clear()
    _locks.clear()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def cached(key: str, ttl: float, factory) -> dict:
    """{'data': 값, 'at': 가져온 시각(ISO)} 를 돌려준다. ttl 안에 같은 key 를 또 부르면 스팀을 다시 부르지 않는다."""
    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    async with _locks.setdefault(key, asyncio.Lock()):
        hit = _cache.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        entry = {"data": await factory(), "at": _now_iso()}
        _cache[key] = (time.monotonic() + ttl, entry)
        if len(_cache) > MAX_CACHE_ENTRIES:  # 오래된 것부터 버린다
            for old in sorted(_cache, key=lambda k: _cache[k][0])[: len(_cache) - MAX_CACHE_ENTRIES]:
                _cache.pop(old, None)
                _locks.pop(old, None)
        return entry


# ---------------------------------------------------------------- 랭킹
async def _build_rankings() -> list[dict]:
    ranks = await steam.fetch_most_played(RANK_COUNT)
    apps = [r["app"] for r in ranks]
    names, *players = await asyncio.gather(steam.fetch_store_names(apps), *(steam.fetch_current_players(a) for a in apps))
    return [
        {
            "rank": r["rank"],
            "app": r["app"],
            "name": names.get(r["app"]) or title_of_app(r["app"]) or f"앱 {r['app']}",
            "players": count,  # 못 가져오면 None -> 프론트가 '집계 대기' 로 표시
            "url": f"https://store.steampowered.com/app/{r['app']}/",
        }
        for r, count in zip(ranks, players)
    ]


# ---------------------------------------------------------------- 뉴스 · 신작 · 할인
def _store_card(x: dict) -> dict:
    return {
        "app": x["id"],
        "title": x["name"],
        "image": x.get("header_image") or x.get("large_capsule_image") or "",
        "discount": x.get("discount_percent") or 0,
        "price": x.get("final_price"),
        "originalPrice": x.get("original_price"),
        "currency": x.get("currency") or "KRW",
        "url": f"https://store.steampowered.com/app/{x['id']}/",
    }


def _games_only(items: list[dict]) -> list[dict]:
    return [x for x in items if x.get("type") == 0 and x.get("id") and x.get("name")]


async def _featured() -> dict:
    return await cached("featured", TTL_FEATURED, steam.fetch_featured)


async def _news_of_game(game: str) -> dict:
    app = app_id_of(game)

    async def build():
        items = await steam.fetch_news(app, NEWS_PER_GAME)
        return [{**x, "game": game, "app": app} for x in items]

    return await cached(f"news:{game}", TTL_NEWS, build)


async def _news_of_games(games: list[str]) -> tuple[list[dict], str]:
    """여러 게임의 소식을 동시에(최대 NEWS_CONCURRENCY개씩) 가져온다. 일부가 실패해도 나머지로 계속한다."""
    gate = asyncio.Semaphore(NEWS_CONCURRENCY)

    async def one(game):
        async with gate:
            return await _news_of_game(game)

    results = await asyncio.gather(*(one(g) for g in games), return_exceptions=True)
    ok = [r for r in results if isinstance(r, dict)]
    failed = [r for r in results if isinstance(r, Exception)]
    for exc in failed:
        log.warning("게임 소식 조회 실패: %s", safe_errors.describe(exc))
    if failed and not ok:
        raise failed[0]
    items = [n for r in ok for n in r["data"]]
    return items, min((r["at"] for r in ok), default=_now_iso())


async def _build_news_bundle(game: str | None) -> tuple[dict, str]:
    games = [game] if game else [g for g in catalog()["news_games"] if g in catalog()["games"]]
    (news, news_at), featured = await asyncio.gather(_news_of_games(games), _featured())
    fd = featured["data"]
    sales = [_store_card(x) for x in _games_only((fd.get("specials") or {}).get("items") or []) if x.get("discounted")]
    new_releases = [_store_card(x) for x in _games_only((fd.get("new_releases") or {}).get("items") or [])]
    data = {
        "news": sorted(news, key=lambda n: n["date"], reverse=True),
        "newReleases": new_releases[:CARD_COUNT],
        "sales": sales[:CARD_COUNT],
    }
    return data, min(news_at, featured["at"])


# ---------------------------------------------------------------- 리뷰 요약
async def _review_summary(game: str) -> dict:
    app = app_id_of(game)

    async def build():
        s = await steam.fetch_review_summary(app)
        return {**s, "url": f"https://store.steampowered.com/app/{app}/#app_reviews_hash"}

    return await cached(f"summary:{game}", TTL_SUMMARY, build)


# ---------------------------------------------------------------- 공개 함수 (라우터가 부른다)
async def get_market(section: str, game: str | None) -> dict:
    """GET /api/market. 모르는 게임 id 면 LookupError."""
    if section == "rankings":
        entry = await cached("rankings", TTL_RANKINGS, _build_rankings)
        return {"section": section, "updatedAt": entry["at"], "data": entry["data"]}
    if section == "news":
        if game:
            app_id_of(game)  # 모르는 id 는 스팀을 부르기 전에 거른다
        data, at = await _build_news_bundle(game)
        return {"section": section, "updatedAt": at, "data": data}
    if section == "reviews":
        if not game:
            raise ValueError("game")
        entry = await _review_summary(game)
        return {"section": section, "updatedAt": entry["at"], "data": entry["data"]}
    raise ValueError("section")


async def get_review_page(game: str, sentiment: str, days: str, language: str, sort: str, cursor: str) -> dict:
    app = app_id_of(game)
    key = f"reviews:{game}:{sentiment}:{days}:{language}:{sort}:{cursor}"
    entry = await cached(key, TTL_REVIEWS, lambda: steam.fetch_review_page(app, sentiment, language, sort, days, cursor))
    return {**entry["data"], "checkedAt": entry["at"]}


async def get_details(game: str) -> dict:
    """스팀이 게임을 찾지 못하면 LookupError."""
    app = app_id_of(game)
    entry = await cached(f"details:{game}", TTL_DETAILS, lambda: steam.fetch_app_details(app))
    if entry["data"] is None:
        raise LookupError(game)
    return {"details": entry["data"]}
