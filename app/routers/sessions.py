from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path

from app import docs
from app.auth import optional_user_id
from app.db import get_supabase, run
from app.schemas import AnswersIn, CompleteIn, SessionCreate
from app.services import games_repo
from app.services.recommender import AXES, recommend
from app.services.report import build_report

router = APIRouter(prefix="/api/sessions", tags=[docs.SESSIONS])

SessionPath = Annotated[UUID, Path(description="진단 세션 id (세션 시작 API 응답의 id)")]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def load_session(session_id: UUID, user_id: str | None) -> dict:
    res = await run(
        lambda: get_supabase().table("diagnosis_sessions").select("*").eq("id", str(session_id)).limit(1).execute()
    )
    if not res.data:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    session = res.data[0]
    # 로그인 사용자의 세션은 본인만, 비회원 세션은 UUID를 아는 사람만 접근
    if session["user_id"] and session["user_id"] != user_id:
        raise HTTPException(403, "접근 권한이 없습니다.")
    return session


@router.post("", status_code=201, **docs.doc("sessions_create"))
async def create_session(body: SessionCreate, user_id: str | None = Depends(optional_user_id)):
    row = {"track": body.track, "user_id": user_id}
    res = await run(lambda: get_supabase().table("diagnosis_sessions").insert(row).execute())
    return res.data[0]


@router.put("/{session_id}/answers", **docs.doc("sessions_answers"))
async def save_answers(session_id: SessionPath, body: AnswersIn, user_id: str | None = Depends(optional_user_id)):
    session = await load_session(session_id, user_id)
    if session["status"] != "in_progress":
        raise HTTPException(409, "이미 종료된 세션입니다.")
    rows = [
        {"session_id": str(session_id), "question_id": a.question_id, "answer": a.answer, "answered_at": _now()}
        for a in body.answers
    ]
    # sql/001_constraints.sql 의 (session_id, question_id) 유니크 인덱스 필요
    await run(
        lambda: get_supabase().table("diagnosis_answers").upsert(rows, on_conflict="session_id,question_id").execute()
    )
    return {"saved": len(rows)}


@router.post("/{session_id}/complete", **docs.doc("sessions_complete"))
async def complete_session(session_id: SessionPath, body: CompleteIn, user_id: str | None = Depends(optional_user_id)):
    session = await load_session(session_id, user_id)
    sid = str(session_id)
    now = _now()

    scores_row = {
        "session_id": sid,
        **{axis: round(value, 1) for axis, value in zip(AXES, body.axes)},
        "platform_fit": {"selected": body.prefs.get("platforms", [])},
        "updated_at": now,
    }
    report = await build_report(body.axes, body.title, session["track"], body.evidence)
    report_row = {
        "session_id": sid,
        "profile_name": report["profile_name"],
        "model_name": report["model_name"],
        "keywords": report["keywords"],
        "summary": report["summary"],
        "detail": report["detail"],
        "anti_match": report["anti_match"],
        "play_tip": report["play_tip"],
        "generated_by": report["generated_by"],
        "updated_at": now,
    }

    games = await games_repo.load_all_games("id,title,genres,tags,platforms")
    recs = [{**r, "session_id": sid} for r in recommend(body.axes, games, body.prefs, limit=10)]

    def persist():
        sb = get_supabase()
        sb.table("analysis_scores").upsert(scores_row, on_conflict="session_id").execute()
        sb.table("analysis_reports").upsert(report_row, on_conflict="session_id").execute()
        sb.table("recommendations").delete().eq("session_id", sid).execute()
        if recs:
            sb.table("recommendations").insert(recs).execute()
        sb.table("diagnosis_sessions").update({"status": "completed", "completed_at": now}).eq("id", sid).execute()

    await run(persist)
    return await _build_result(sid)


@router.get("/{session_id}/result", **docs.doc("sessions_result"))
async def get_result(session_id: SessionPath, user_id: str | None = Depends(optional_user_id)):
    await load_session(session_id, user_id)
    return await _build_result(str(session_id))


async def _build_result(sid: str) -> dict:
    def fetch():
        sb = get_supabase()
        return (
            sb.table("diagnosis_sessions").select("*").eq("id", sid).limit(1).execute(),
            sb.table("analysis_scores").select("*").eq("session_id", sid).limit(1).execute(),
            sb.table("analysis_reports").select("*").eq("session_id", sid).limit(1).execute(),
            sb.table("recommendations")
            .select("rank,match_score,reason,matched_tags,algorithm_version,"
                    "games(id,title,cover_url,genres,platforms,release_date)")
            .eq("session_id", sid)
            .order("rank")
            .execute(),
        )

    session, scores, report, recs = await run(fetch)
    return {
        "session": session.data[0] if session.data else None,
        "scores": scores.data[0] if scores.data else None,
        "report": report.data[0] if report.data else None,
        "recommendations": recs.data,
    }
