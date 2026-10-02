"""AI 활용방안 문서의 기능 API.  모든 문장 생성은 Ollama, 점수/필터/일정 계산은 코드가 한다."""
import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app import docs
from app.auth import optional_user_id, require_admin
from app.db import get_supabase, run
from app.routers.sessions import load_session
from app.schemas import AiSearchIn, BacklogIn, ExplainIn, ReviewSummaryIn, ScheduleIn, SimilarIn
from app.services import ai_features as ai
from app.services import aliases, games_repo, games_sync, safe_errors, steam

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=[docs.AI])

GAME_COLS = "id,title,description,genres,tags,platforms,release_date,playtime_hours,price_info,cover_url,steam_app_id"
AXES = ["physical", "strategy", "exploration", "emotion", "comfort", "competition"]


async def _all_games() -> list[dict]:
    return await games_repo.load_all_games(GAME_COLS)


async def _resolve(title: str, games: list[dict]) -> dict | None:
    """DB에서 제목으로 찾고, 없으면 RAWG/IGDB에서 가져와 저장한다."""
    found = ai.find_game(games, title)  # 한국어 이름이면 별칭표로 영어 제목을 먼저 찾는다
    if found:
        return found
    row = await games_sync.ensure_game(aliases.canonical(title))
    if row:
        games.append(row)
    return row


async def _shape_results(results: list[dict], context: dict, explain: bool, top_n: int = 3) -> list[dict]:
    async def one(r: dict) -> None:
        fallback = ai.rule_reason(r["game"], r["matched"])
        r["reason"], r["reason_source"] = await ai.explain_game(context, r["game"], fallback, matched=r["matched"])

    # 상위 top_n 중 점수가 충분히 높은 것에만 AI 설명을 쓴다 (점수가 낮으면 억지 설명이 환각을 만든다)
    targets = [r for r in results[:top_n] if r["score"] >= ai.EXPLAIN_MIN_SCORE] if explain else []
    await asyncio.gather(*[one(r) for r in targets])
    for r in results:
        if "reason" not in r:
            r["reason"], r["reason_source"] = ai.rule_reason(r["game"], r["matched"]), "rule"
    return [
        {"game": ai.public_game(r["game"]), "score": r["score"], "matched": r["matched"],
         "reason": r["reason"], "reason_source": r["reason_source"]}
        for r in results
    ]


# ---------------------------------------------------------------- 자연어 검색 / 대체제 찾기
@router.post("/search", **docs.doc("ai_search"))
async def natural_language_search(body: AiSearchIn):
    """"친구 3명이서 주말에 웃으면서 할 수 있는 사양 낮은 게임", "스위치 없는데 동물의 숲 같은 게임" 같은 문장 검색."""
    games = await _all_games()
    intent = await ai.parse_search_intent(body.query, ai.vocabulary(games), games)

    liked, missing = [], []
    for title in intent["liked_games"]:
        g = await _resolve(title, games)
        (liked if g else missing).append(g or title)

    found = ai.search_games(games, intent, liked, date.today(), body.limit)
    context = {"query": body.query, "liked": [g["title"] for g in liked]}
    return {
        "intent": intent,
        "liked_games": [g["title"] for g in liked],
        "liked_games_not_found": missing,
        "results": await _shape_results(found, context, body.explain),
    }


@router.post("/similar", **docs.doc("ai_similar"))
async def similar_games(body: SimilarIn):
    """내가 재밌게 한 게임과 비슷한 게임 / 비싼·옛날 게임의 대체제(인디, 할인, 최신 등)."""
    games = await _all_games()
    liked, missing = [], []
    for title in body.titles:
        g = await _resolve(title, games)
        (liked if g else missing).append(g or title)
    if not liked:
        raise HTTPException(404, f"게임을 찾지 못했습니다: {', '.join(missing)}")

    intent = {
        "genres": [], "tags": [],
        "platforms": ai.norm_platforms(body.platforms),
        "exclude_platforms": ai.norm_platforms(body.exclude_platforms),
        "prefer": {k: k in body.prefer for k in ai.PREFER_KEYS},
        "max_hours": None,
    }
    found = ai.search_games(games, intent, liked, date.today(), body.limit)
    context = {"liked": [g["title"] for g in liked], "prefer": body.prefer}
    return {
        "liked_games": [g["title"] for g in liked],
        "liked_games_not_found": missing,
        "results": await _shape_results(found, context, body.explain),
    }


# ---------------------------------------------------------------- 추천 이유
@router.post("/explain", **docs.doc("ai_explain"))
async def explain_recommendation(body: ExplainIn, user_id: str | None = Depends(optional_user_id)):
    """진단 결과로 추천된 게임에 대해 'AI가 쓴 추천 이유'를 만들어 recommendations.reason 에 저장한다."""
    await load_session(body.session_id, user_id)
    sid, gid = str(body.session_id), str(body.game_id)

    def fetch():
        sb = get_supabase()
        return (
            sb.table("recommendations").select("*").eq("session_id", sid).eq("game_id", gid).limit(1).execute(),
            sb.table("games").select("*").eq("id", gid).limit(1).execute(),
            sb.table("analysis_reports").select("profile_name,keywords").eq("session_id", sid).limit(1).execute(),
            sb.table("analysis_scores").select("*").eq("session_id", sid).limit(1).execute(),
        )

    rec, game, report, scores = await run(fetch)
    if not rec.data or not game.data:
        raise HTTPException(404, "이 세션의 추천 목록에 없는 게임입니다.")

    context: dict = {}
    if report.data:
        context.update(profile_name=report.data[0].get("profile_name"), keywords=report.data[0].get("keywords"))
    if scores.data:
        context["top_axes"] = ai.axes_summary([float(scores.data[0][a]) for a in AXES])

    fallback = rec.data[0].get("reason") or ai.rule_reason(game.data[0], rec.data[0].get("matched_tags") or [])
    text, source = await ai.explain_game(context, game.data[0], fallback, matched=rec.data[0].get("matched_tags") or [])
    if source == "ollama":
        await run(lambda: get_supabase().table("recommendations").update({"reason": text})
                  .eq("session_id", sid).eq("game_id", gid).execute())
    return {"reason": text, "source": source}


# ---------------------------------------------------------------- 백로그 처리반
@router.post("/backlog", **docs.doc("ai_backlog"))
async def backlog_picker(body: BacklogIn):
    """내 라이브러리(스팀 연동 또는 직접 입력한 5~10개 이상)에서 지금 할 게임 하나 고르기."""
    entries: list[tuple[str, int | None]] = []
    if body.steam_id:
        try:
            entries += [(g["name"], g["playtime_minutes"]) for g in await steam.fetch_owned_games(body.steam_id)]
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        except RuntimeError as exc:
            raise HTTPException(503, str(exc))
        except Exception as exc:
            log.warning("스팀 라이브러리 조회 실패: %s", safe_errors.describe(exc))
            raise HTTPException(502, "스팀에서 라이브러리를 가져오지 못했습니다. 프로필의 게임 목록이 공개인지 확인하세요.")
    entries += [(t, None) for t in body.games]
    seen, unique = set(), []
    for title, minutes in entries:
        k = ai.norm_title(title)
        if k and k not in seen:
            seen.add(k)
            unique.append((title, minutes))
    if not unique:
        raise HTTPException(422, "games(게임 제목 목록) 또는 steam_id 가 필요합니다.")
    # 라이브러리가 크면 플레이 시간이 적은(=아직 안 한) 게임 위주로 80개만 AI에게 보여준다
    unique.sort(key=lambda x: (x[1] is None, x[1] or 0))
    unique = unique[:80]

    games = await _all_games()
    cands, matched = [], 0
    for title, minutes in unique:
        g = ai.find_game(games, title, cutoff=0.85)
        matched += bool(g)
        cands.append({
            "title": title, "genres": (g or {}).get("genres") or [], "tags": (g or {}).get("tags") or [],
            "playtime_hours": (g or {}).get("playtime_hours"), "my_playtime_minutes": minutes,
        })
    result = await ai.pick_backlog(cands, body.mood, body.minutes)
    return {**result, "candidates_considered": len(cands), "matched_in_db": matched}


# ---------------------------------------------------------------- 플레이타임 계산기
@router.post("/schedule", **docs.doc("ai_schedule"))
async def play_schedule(body: ScheduleIn):
    """엔딩까지 걸리는 시간과 사용자의 여유 시간으로 현실적인 일정을 계산한다 (계산은 코드, 설명 문장만 AI)."""
    games = await _all_games()
    if body.game_id:
        game = next((g for g in games if g["id"] == str(body.game_id)), None)
    elif body.title:
        game = await _resolve(body.title, games)
    else:
        raise HTTPException(422, "game_id 또는 title 이 필요합니다.")
    if not game:
        raise HTTPException(404, "게임을 찾을 수 없습니다.")
    if not game.get("playtime_hours"):
        raise HTTPException(422, "이 게임은 플레이타임 데이터가 없어 일정을 계산할 수 없습니다.")

    parsed = ai.parse_availability(body.text or "")
    hpd = body.hours_per_day or parsed["hours_per_day"]
    dpw = body.days_per_week or parsed["days_per_week"]
    if not hpd:
        raise HTTPException(422, "하루에 쓸 수 있는 시간을 알려주세요. 예: text='주말에 하루 2시간'")
    assumptions = []
    if dpw is None:
        dpw = 7.0
        assumptions.append("요일 정보가 없어 매일 플레이한다고 가정했어요.")

    plan = ai.schedule_math(float(game["playtime_hours"]), float(hpd), float(dpw), date.today())
    alts = ai.shorter_alternatives(games, game, float(hpd)) if plan["weeks"] > 4 else []
    text, source = await ai.schedule_message(game, plan, alts)
    return {
        "game": ai.public_game(game), "plan": plan, "assumptions": assumptions,
        "shorter_alternatives": [
            {"game": ai.public_game(a["game"]), "play_sessions": a["play_sessions"], "similarity": a["similarity"]}
            for a in alts
        ],
        "message": text, "message_source": source,
        "note": "플레이타임은 RAWG 등 외부 데이터의 평균값이라 실제와 다를 수 있어요.",
    }


# ---------------------------------------------------------------- 리뷰 요약
@router.post("/review-summary", **docs.doc("ai_review"))
async def review_summary(body: ReviewSummaryIn):
    """리뷰 장단점 요약. reviews 를 보내거나, 보내지 않으면 steam_app_id 가 있는 게임은 스팀 공개 리뷰를 가져온다."""
    res = await run(lambda: get_supabase().table("games").select("id,title,steam_app_id")
                    .eq("id", str(body.game_id)).limit(1).execute())
    if not res.data:
        raise HTTPException(404, "게임을 찾을 수 없습니다.")
    game = res.data[0]

    reviews = body.reviews
    if not reviews:
        if not game.get("steam_app_id"):
            raise HTTPException(422, "reviews 를 보내거나 steam_app_id 가 있는 게임이어야 합니다.")
        try:
            reviews = [r["text"] for r in await steam.fetch_reviews(int(game["steam_app_id"]))]
        except Exception as exc:
            log.warning("스팀 리뷰 조회 실패: %s", safe_errors.describe(exc))
            raise HTTPException(502, "스팀에서 리뷰를 가져오지 못했습니다.")
    try:
        summary = await ai.summarize_reviews(game["title"], reviews)
    except ValueError as exc:
        raise HTTPException(502 if "리뷰가" not in str(exc) else 422, f"리뷰 요약 실패: {exc}")
    except Exception as exc:
        log.warning("리뷰 요약 LLM 실패: %s", safe_errors.describe(exc))
        raise HTTPException(503, "AI 서버에서 요약을 만들지 못했습니다.")
    return {"game": {"id": game["id"], "title": game["title"]}, **summary}


# ---------------------------------------------------------------- 할인 / 출시 예정 탭
@router.get("/deals", **docs.doc("ai_deals"))
async def personalized_deals(
    session_id: Annotated[UUID, Query(description="진단 세션 id (세션 시작 API 응답의 id). 진단을 완료한 세션이어야 함")],
    limit: int = Query(default=10, ge=1, le=30, description="할인·출시예정 각각 돌려받을 개수"),
    user_id: str | None = Depends(optional_user_id),
):
    """진단 결과(6축)와 잘 맞는 할인 중 게임 / 출시 예정 게임을 위로 정렬한다. games.price_info 가 채워져 있어야 한다."""
    await load_session(session_id, user_id)
    sc = await run(lambda: get_supabase().table("analysis_scores").select("*").eq("session_id", str(session_id)).limit(1).execute())
    if not sc.data:
        raise HTTPException(409, "진단을 먼저 완료해야 합니다.")
    axes = [float(sc.data[0][a]) for a in AXES]
    return ai.rank_deals(await _all_games(), axes, date.today(), limit)


@router.post("/admin/sync-prices", dependencies=[Depends(require_admin)], **docs.doc("ai_sync_prices"))
async def sync_prices(cc: str = Query(default="kr", min_length=2, max_length=2, description="국가 코드 2글자 (kr=한국 원화, us=미국 달러)")):
    """steam_app_id 가 있는 게임의 가격/할인 정보를 스팀에서 가져와 games.price_info 에 저장한다 (X-Admin-Token 필요)."""
    games = [g for g in await _all_games() if g.get("steam_app_id")]
    prices = await steam.fetch_prices([int(g["steam_app_id"]) for g in games], cc=cc)
    updated = 0
    now = datetime.now(timezone.utc).isoformat()
    for g in games:
        info = prices.get(int(g["steam_app_id"]))
        if info:
            await run(lambda i=info, gid=g["id"]: get_supabase().table("games")
                      .update({"price_info": i, "updated_at": now}).eq("id", gid).execute())
            updated += 1
    return {"games_with_steam_id": len(games), "updated": updated}
