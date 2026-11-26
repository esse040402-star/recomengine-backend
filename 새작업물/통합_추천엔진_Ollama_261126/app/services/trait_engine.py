"""DB-backed six-axis taste scoring.

The survey option and game tag weights live in Supabase.  The frontend still
sends option indexes (0-based); recommendationService maps its local q/p IDs
onto the canonical survey_questions IDs before persisting answers.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

from app.db import get_supabase, run

log = logging.getLogger(__name__)
AXES = ("physical", "strategy", "exploration", "emotion", "comfort", "competition")
STAGE_WEIGHTS = {"ONB": 0.55, "PROFILE": 1.4}
_CANONICAL_ID = re.compile(r"^(G|NG)_(ONB|PROFILE)_[0-9]{2}$")


def _answer_indexes(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    indexes: list[int] = []
    for item in value:
        try:
            index = int(item)
        except (TypeError, ValueError):
            continue
        if index >= 0 and index not in indexes:
            indexes.append(index)
    return indexes


def calculate_session_scores(session_id: str) -> dict[str, Any]:
    """Calculate and persist normalized trait scores from canonical survey answers."""
    sb = get_supabase()
    answers = (
        sb.table("diagnosis_answers")
        .select("question_id,answer")
        .eq("session_id", session_id)
        .execute()
        .data
        or []
    )
    canonical = [a for a in answers if _CANONICAL_ID.match(str(a.get("question_id", "")))]
    if not canonical:
        return {"scores": {}, "axes": None, "mapped_questions": 0}

    qids = sorted({a["question_id"] for a in canonical})
    options = (
        sb.table("survey_options")
        .select("option_id,question_id,option_order")
        .in_("question_id", qids)
        .execute()
        .data
        or []
    )
    option_by_question_order = {
        (row["question_id"], int(row["option_order"])): row["option_id"] for row in options
    }
    selected_option_ids: dict[str, list[str]] = {}
    for answer in canonical:
        selected_option_ids[answer["question_id"]] = [
            option_by_question_order[(answer["question_id"], idx)]
            for idx in _answer_indexes(answer.get("answer"))
            if (answer["question_id"], idx) in option_by_question_order
        ]
    option_ids = sorted({oid for ids in selected_option_ids.values() for oid in ids})
    if not option_ids:
        return {"scores": {}, "axes": None, "mapped_questions": 0}

    mappings = (
        sb.table("option_trait_scores")
        .select("option_id,trait_id,base_weight")
        .in_("option_id", option_ids)
        .execute()
        .data
        or []
    )
    traits = sb.table("taste_traits").select("trait_id,trait_name").execute().data or []
    trait_names = {t["trait_id"]: t["trait_name"] for t in traits}
    by_option: dict[str, list[dict]] = defaultdict(list)
    for row in mappings:
        by_option[row["option_id"]].append(row)

    weighted_sum: dict[str, float] = defaultdict(float)
    total_weight: dict[str, float] = defaultdict(float)
    mapped_questions = 0
    for question_id, selected_ids in selected_option_ids.items():
        match = _CANONICAL_ID.match(question_id)
        if not match or not selected_ids:
            continue
        stage_weight = STAGE_WEIGHTS[match.group(2)]
        per_trait: dict[str, list[float]] = defaultdict(list)
        for option_id in selected_ids:
            for row in by_option.get(option_id, []):
                name = trait_names.get(row["trait_id"])
                if name in AXES:
                    per_trait[name].append(float(row["base_weight"]))
        if not per_trait:
            continue
        mapped_questions += 1
        for name, values in per_trait.items():
            weighted_sum[name] += (sum(values) / len(values)) * stage_weight
            total_weight[name] += stage_weight

    scores = {
        name: round(weighted_sum[name] / total_weight[name], 2) if total_weight[name] else 50.0
        for name in AXES
    }
    trait_ids = {t["trait_name"]: t["trait_id"] for t in traits if t["trait_name"] in AXES}
    rows = [
        {"session_id": session_id, "trait_id": trait_ids[name], "trait_score": scores[name]}
        for name in AXES
        if name in trait_ids
    ]
    if rows:
        sb.table("survey_trait_scores").upsert(rows, on_conflict="session_id,trait_id").execute()
    return {"scores": scores, "axes": [scores[name] for name in AXES] if mapped_questions else None, "mapped_questions": mapped_questions}


def load_game_trait_vectors(game_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not game_ids:
        return {}
    sb = get_supabase()
    rows = (
        sb.table("game_trait_scores")
        .select("game_id,trait_id,trait_score,score_evidence")
        .in_("game_id", game_ids)
        .execute()
        .data
        or []
    )
    traits = sb.table("taste_traits").select("trait_id,trait_name").execute().data or []
    names = {t["trait_id"]: t["trait_name"] for t in traits}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        game = result.setdefault(row["game_id"], {"scores": {}, "matched_tags": set()})
        trait_name = names.get(row["trait_id"])
        if trait_name in AXES:
            game["scores"][trait_name] = float(row["trait_score"])
        evidence = row.get("score_evidence") or {}
        game["matched_tags"].update(evidence.get("matched_tags") or [])
    for game in result.values():
        game["vector"] = [game["scores"].get(axis, 50.0) for axis in AXES]
        game["matched_tags"] = sorted(game["matched_tags"])
    return result


def refresh_game_traits_many(games: list[dict[str, Any]]) -> int:
    """Recalculate a batch of game vectors from DB tag rules (one rules query)."""
    if not games:
        return 0
    sb = get_supabase()
    rules = sb.table("game_trait_tag_rules").select("normalized_tag_name,trait_id,weight").execute().data or []
    if not rules:
        return 0
    rows = []
    game_ids = []
    for game in games:
        game_id = str(game["id"])
        game_ids.append(game_id)
        tags = {
            str(tag).strip().casefold()
            for tag in (game.get("genres") or []) + (game.get("tags") or [])
            if str(tag).strip()
        }
        matched: dict[str, list[tuple[float, str]]] = defaultdict(list)
        for rule in rules:
            tag = str(rule.get("normalized_tag_name") or "").casefold()
            if tag and tag in tags:
                matched[rule["trait_id"]].append((float(rule["weight"]), tag))
        for trait_id, values in matched.items():
            rows.append({
                "game_id": game_id,
                "trait_id": trait_id,
                "trait_score": round(sum(value for value, _ in values) / len(values), 2),
                "score_evidence": {"matched_tags": sorted({tag for _, tag in values})},
            })

    # Scores are a derived cache. Remove stale trait rows only for the games being refreshed.
    for start in range(0, len(game_ids), 200):
        sb.table("game_trait_scores").delete().in_("game_id", game_ids[start : start + 200]).execute()
    for start in range(0, len(rows), 200):
        sb.table("game_trait_scores").upsert(rows[start : start + 200], on_conflict="game_id,trait_id").execute()
    return len(rows)


def refresh_game_traits(game: dict[str, Any]) -> int:
    return refresh_game_traits_many([game])


async def calculate_session_scores_async(session_id: str) -> dict[str, Any]:
    return await run(lambda: calculate_session_scores(session_id))


async def load_game_trait_vectors_async(game_ids: list[str]) -> dict[str, dict[str, Any]]:
    return await run(lambda: load_game_trait_vectors(game_ids))


async def refresh_game_traits_async(game: dict[str, Any]) -> int:
    return await run(lambda: refresh_game_traits(game))


async def refresh_game_traits_many_async(games: list[dict[str, Any]]) -> int:
    return await run(lambda: refresh_game_traits_many(games))
