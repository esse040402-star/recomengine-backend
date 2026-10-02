import asyncio
import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.db import get_supabase, run
from app.services import game_clean, igdb, rawg, safe_errors

log = logging.getLogger(__name__)


def _dedupe(*lists: list[str]) -> list[str]:
    seen, out = set(), []
    for lst in lists:
        for x in lst:
            k = x.lower()
            if k not in seen:
                seen.add(k)
                out.append(x)
    return out


def _merge_igdb(row: dict, extra: dict) -> dict:
    e = igdb.to_game_row(extra)
    row["igdb_id"] = e["igdb_id"]
    row["description"] = row.get("description") or e["description"]
    row["cover_url"] = row.get("cover_url") or e["cover_url"]
    row["release_date"] = row.get("release_date") or e["release_date"]
    row["genres"] = _dedupe(row["genres"], e["genres"])
    row["tags"] = _dedupe(row["tags"], e["tags"])
    row["platforms"] = _dedupe(row["platforms"], e["platforms"])
    row["source_data"] = {**row["source_data"], **e["source_data"]}
    return row


def _external_error(service: str, exc: Exception) -> HTTPException:
    log.warning("%s 요청 실패: %s", service, safe_errors.describe(exc))
    code = 503 if isinstance(exc, httpx.RequestError) else 502
    return HTTPException(code, f"{service}: {safe_errors.status_hint(exc)}")


async def sync_by_query(query: str, limit: int = 10, platform: str | None = None, include_minor: bool = False) -> dict:
    """검색어로 게임을 가져와 정리한 뒤 games 테이블에 저장한다.
    반환: saved(저장한 제목), skipped(비공식/저품질이라 건너뛴 제목), failed(저장 실패)"""
    s = get_settings()
    rows: list[dict] = []
    skipped: list[str] = []

    if s.rawg_enabled:
        try:
            hits = await rawg.search(query, limit, platform)
        except Exception as exc:
            raise _external_error("RAWG", exc)
        for hit in hits:
            if not include_minor and game_clean.is_minor_rawg_entry(hit):
                skipped.append(hit.get("name") or str(hit.get("id")))
                continue
            try:
                row = rawg.to_game_row(await rawg.detail(hit["id"]))
            except Exception as exc:
                log.warning("RAWG 상세 조회 실패(%s): %s", hit.get("name"), safe_errors.describe(exc))
                continue
            app_id = await rawg.steam_app_id(hit["id"])
            if app_id:
                row["steam_app_id"] = app_id
            if s.igdb_enabled:
                try:
                    extra = await igdb.find_game(row["title"])
                    if extra:
                        row = _merge_igdb(row, extra)
                    await asyncio.sleep(0.3)  # IGDB 무료 한도(초당 4회) 보호
                except Exception as exc:
                    log.warning("IGDB 보강 실패(%s): %s", row["title"], safe_errors.describe(exc))
            rows.append(game_clean.clean_row(row))
        conflict = "rawg_id"
    elif s.igdb_enabled:
        try:
            found = await igdb.search_many(query, limit)
        except Exception as exc:
            raise _external_error("IGDB", exc)
        rows = [game_clean.clean_row(igdb.to_game_row(g)) for g in found]
        conflict = "igdb_id"
    else:
        raise HTTPException(503, "RAWG_API_KEY 또는 IGDB 키가 설정되어 있지 않습니다.")

    saved, failed = [], []
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        row["updated_at"] = now
        try:
            await run(lambda r=row: get_supabase().table("games").upsert(r, on_conflict=conflict).execute())
            saved.append(row["title"])
        except Exception as exc:
            log.warning("games upsert 실패(%s): %s", row["title"], type(exc).__name__)
            failed.append({"title": row["title"], "error": str(exc)[:200]})
    return {"saved": saved, "skipped": skipped, "failed": failed}


async def ensure_game(title: str) -> dict | None:
    """DB에 없는 게임을 RAWG(+IGDB)에서 찾아 games 테이블에 저장하고 그 행을 돌려준다. 실패하면 None."""
    s = get_settings()
    if not (s.rawg_enabled or s.igdb_enabled):
        return None
    try:
        res = await sync_by_query(title, limit=1)
    except Exception as exc:
        log.warning("ensure_game 실패(%s): %s", title, safe_errors.describe(exc))
        return None
    if not res["saved"]:
        return None
    saved_title = res["saved"][0]
    found = await run(lambda: get_supabase().table("games").select("*").eq("title", saved_title).limit(1).execute())
    return found.data[0] if found.data else None
