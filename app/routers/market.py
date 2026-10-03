import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app import docs
from app.services import market, safe_errors

router = APIRouter(prefix="/api", tags=[docs.MARKET])
log = logging.getLogger(__name__)

UNKNOWN_GAME = "알 수 없는 게임이에요. 게임 목록이 바뀌었다면 python -m scripts.export_catalog 로 대응표를 다시 만들어야 해요."


async def _guard(label: str, coro):
    """모르는 게임은 404, 스팀 쪽 문제는 502 로 바꾼다 (로그에는 키가 새지 않게 종류와 상태 코드만 남긴다)."""
    try:
        return await coro
    except LookupError:
        raise HTTPException(404, UNKNOWN_GAME)
    except Exception as exc:
        log.warning("%s 조회 실패: %s", label, safe_errors.describe(exc))
        raise HTTPException(502, f"스팀에서 {label}을(를) 가져오지 못했어요. {safe_errors.status_hint(exc)}")


@router.get("/market", **docs.doc("market"))
async def get_market(
    section: Literal["rankings", "news", "reviews"] = Query(description="가져올 묶음: rankings(인기 순위) · news(소식·신작·할인) · reviews(추천 비율)"),
    game: str | None = Query(default=None, max_length=60, description="프론트 게임 id (예: elden). reviews 에는 필수, news 에서는 그 게임 소식만 가져옴"),
):
    if section == "reviews" and not game:
        raise HTTPException(422, "리뷰 집계에는 game(게임 id)이 필요해요.")
    labels = {"rankings": "인기 순위", "news": "소식", "reviews": "리뷰 집계"}
    return await _guard(labels[section], market.get_market(section, game))


@router.get("/steam/reviews", **docs.doc("steam_reviews"))
async def steam_reviews(
    game: str = Query(max_length=60, description="프론트 게임 id (예: elden)"),
    sentiment: Literal["all", "positive", "negative"] = Query(default="all", description="all(전체) · positive(추천) · negative(비추천)"),
    days: Literal["all", "30", "180", "365"] = Query(default="all", description="작성 기간: all(전체) 또는 최근 며칠 (30 · 180 · 365)"),
    language: Literal["all", "koreana", "english"] = Query(default="all", description="리뷰 언어: all · koreana(한국어) · english(영어)"),
    sort: Literal["recent", "helpful"] = Query(default="recent", description="recent(최신순) · helpful(도움순)"),
    cursor: str = Query(default="*", max_length=200, description="다음 페이지 표식. 처음은 * , 이후는 직전 응답의 cursor"),
):
    return await _guard("리뷰", market.get_review_page(game, sentiment, days, language, sort, cursor))


@router.get("/steam/details", **docs.doc("steam_details"))
async def steam_details(
    game: str = Query(max_length=60, description="프론트 게임 id (예: elden)"),
):
    return await _guard("게임 정보", market.get_details(game))
