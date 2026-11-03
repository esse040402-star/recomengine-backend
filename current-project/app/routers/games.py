from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app import docs
from app.auth import require_admin
from app.db import get_supabase, run
from app.schemas import GameSyncIn
from app.services import games_sync

router = APIRouter(prefix="/api", tags=[docs.GAMES])

LIST_COLUMNS = "id,title,cover_url,genres,tags,platforms,release_date,playtime_hours,rawg_id,igdb_id"


@router.get("/games", **docs.doc("games_list"))
async def list_games(
    q: str | None = Query(default=None, max_length=100, description="제목 검색어 (일부만 써도 됨, 예: elden)"),
    genre: str | None = Query(default=None, max_length=50, description="장르 이름 정확히 (예: RPG, Puzzle)"),
    limit: int = Query(default=24, ge=1, le=100, description="한 번에 가져올 개수 (1~100)"),
    offset: int = Query(default=0, ge=0, description="앞에서부터 건너뛸 개수 (다음 페이지는 limit 만큼 늘리기)"),
):
    def query():
        qb = get_supabase().table("games").select(LIST_COLUMNS, count="exact")
        if q:
            safe = q.replace("%", " ").replace(",", " ").strip()
            qb = qb.ilike("title", f"%{safe}%")
        if genre:
            qb = qb.contains("genres", [genre])
        return qb.order("title").range(offset, offset + limit - 1).execute()

    res = await run(query)
    return {"items": res.data, "total": res.count, "limit": limit, "offset": offset}


@router.get("/games/{game_id}", **docs.doc("games_detail"))
async def get_game(game_id: Annotated[UUID, Path(description="게임 id (목록 API 응답의 id)")]):
    res = await run(lambda: get_supabase().table("games").select("*").eq("id", str(game_id)).limit(1).execute())
    if not res.data:
        raise HTTPException(404, "게임을 찾을 수 없습니다.")
    return res.data[0]


@router.post("/admin/games/sync", dependencies=[Depends(require_admin)], **docs.doc("games_sync"))
async def sync_games(body: GameSyncIn):
    """RAWG(+IGDB)에서 검색어에 맞는 게임을 가져와 games 테이블에 upsert 한다.
    헤더 X-Admin-Token 필요."""
    return await games_sync.sync_by_query(body.query, body.limit, body.platform, body.include_minor)
