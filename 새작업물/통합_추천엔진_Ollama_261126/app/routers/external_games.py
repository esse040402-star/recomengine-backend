import logging

from fastapi import APIRouter, HTTPException, Path, Query

from app import docs
from app import docs
from app.services import external_games, safe_errors

router = APIRouter(prefix="/api/external-games", tags=[docs.GAMES])
log = logging.getLogger(__name__)


@router.get("", **docs.doc("external_games_search"))
async def search_games(
    q: str = Query(min_length=1, max_length=100, description="게임 이름 검색"),
    page: int = Query(default=1, ge=1, description="검색 결과 페이지 번호 (기본값 1)"),
    size: int = Query(default=20, ge=1, le=50, description="페이지당 결과 수 (최대 50개)"),
):
    try:
        return await external_games.search_external_games(q, page, size)
    except Exception as exc:
        log.warning("외부 게임 검색 실패: %s", safe_errors.describe(exc))
        raise HTTPException(502, "외부 게임 검색 서버에 연결하지 못했어요.")


@router.get("/{appid}", **docs.doc("external_games_detail"))
async def get_game(appid: int = Path(description="상세 조회할 게임의 외부 ID")):
    try:
        result = await external_games.get_external_game(appid)
        if not result:
            raise HTTPException(404, "게임을 찾을 수 없어요.")
        if not external_games.supports_pc_or_console(result):
            raise HTTPException(404, "PC 또는 콘솔 버전이 있는 게임만 조회할 수 있어요.")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        log.warning("외부 게임 상세 조회 실패: %s", safe_errors.describe(exc))
        raise HTTPException(502, "외부 게임 정보를 가져오지 못했어요.")
