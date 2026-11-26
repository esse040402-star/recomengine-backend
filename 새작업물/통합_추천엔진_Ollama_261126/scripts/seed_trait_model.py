"""Seed the DB-backed taste model (six traits, survey options and tag rules).

Run from the project root after survey_questions has been seeded:
    python -m scripts.seed_trait_model
This script uses the service-role connection configured in .env.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings
from app.db import get_supabase
from app.services.recommender import AXES, AXIS_LABELS, SIGNALS
from app.services.trait_engine import refresh_game_traits_many
from scripts.import_game_trait_scores import import_game_trait_scores

ROOT = Path(__file__).resolve().parents[1]


def chunks(items: list[dict], size: int = 200):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def main() -> None:
    settings = get_settings()
    if settings.use_mock_db:
        raise SystemExit("USE_MOCK_DB=true 입니다. 실제 Supabase 연결(.env)을 설정한 뒤 실행하세요.")

    questions = json.loads((ROOT / "data" / "survey_questions.json").read_text(encoding="utf-8"))
    mapping_doc = json.loads((ROOT / "data" / "trait_mappings.json").read_text(encoding="utf-8"))
    sb = get_supabase()

    existing = sb.table("survey_questions").select("id").limit(1).execute().data
    if not existing:
        raise SystemExit("survey_questions가 비어 있습니다. 먼저 python -m scripts.seed_survey_questions 를 실행하세요.")

    trait_rows = [
        {"trait_name": axis, "description": AXIS_LABELS[axis]}
        for axis in AXES
    ]
    existing_traits = sb.table("taste_traits").select("trait_name").execute().data or []
    existing_names = {row["trait_name"] for row in existing_traits}
    missing_traits = [row for row in trait_rows if row["trait_name"] not in existing_names]
    if missing_traits:
        sb.table("taste_traits").insert(missing_traits).execute()
    # Preserve any descriptions already curated in the live project.
    trait_data = sb.table("taste_traits").select("trait_id,trait_name").execute().data or []
    trait_ids = {row["trait_name"]: row["trait_id"] for row in trait_data}

    option_rows = []
    for question in questions:
        for index, option in enumerate(question.get("options") or []):
            option_rows.append({
                "question_id": question["id"],
                "option_text": str(option),
                "option_order": index,  # frontend option IDs are zero-based strings
            })
    for batch in chunks(option_rows):
        sb.table("survey_options").upsert(batch, on_conflict="question_id,option_order").execute()

    options = sb.table("survey_options").select("option_id,question_id,option_order").execute().data or []
    if not options:
        raise SystemExit("survey_options가 비어 있습니다. supabase/seed.sql을 먼저 적용하세요.")
    option_ids = {(row["question_id"], int(row["option_order"])): row["option_id"] for row in options}

    mapping_rows = []
    for item in mapping_doc["mappings"]:
        prefix = "G" if item["track"] == "gamer" else "NG"
        stage = "ONB" if item["stage"] == "onboarding" else "PROFILE"
        question_id = f"{prefix}_{stage}_{int(item['question_no']):02d}"
        for index, scores in enumerate(item.get("option_scores") or []):
            option_id = option_ids.get((question_id, index))
            if not option_id:
                continue
            for trait_name, score in scores.items():
                if trait_name in trait_ids:
                    mapping_rows.append({
                        "option_id": option_id,
                        "trait_id": trait_ids[trait_name],
                        "base_weight": float(score),
                    })

    # These rows are generated configuration, so replace only mappings for the
    # canonical survey options; user answers and profile data are untouched.
    canonical_option_ids = [
        row["option_id"] for row in options
        if row["question_id"].startswith(("G_ONB_", "NG_ONB_", "G_PROFILE_", "NG_PROFILE_"))
    ]
    for batch in chunks([{"option_id": value} for value in canonical_option_ids]):
        sb.table("option_trait_scores").delete().in_("option_id", [x["option_id"] for x in batch]).execute()
    for batch in chunks(mapping_rows):
        sb.table("option_trait_scores").upsert(batch, on_conflict="option_id,trait_id").execute()

    tag_rules = []
    for tag_name, scores in SIGNALS.items():
        for trait_name, weight in scores.items():
            if trait_name in trait_ids and float(weight) > 0:
                tag_rules.append({
                    "tag_name": tag_name,
                    
                    "trait_id": trait_ids[trait_name],
                    "weight": float(weight),
                })
    for batch in chunks(tag_rules):
        sb.table("game_trait_tag_rules").upsert(batch, on_conflict="normalized_tag_name,trait_id").execute()

    games = sb.table("games").select("id,genres,tags").execute().data or []
    refreshed = refresh_game_traits_many(games)
    # 1,284개 검토된 v5 게임 점수를 Steam AppID로 기존 games.id에 연결해
    # 태그 규칙 기반 임시 점수보다 우선 적용한다. 사용자 설문 답변은 건드리지 않는다.
    imported = import_game_trait_scores(sb=sb)

    print(f"취향 축: {len(trait_ids)}개")
    print(f"설문 선택지: {len(option_rows)}개")
    print(f"선택지-취향 가중치: {len(mapping_rows)}개")
    print(f"게임 태그 규칙: {len(tag_rules)}개")
    print(f"기존 게임 점수 행 갱신: {refreshed}개 ({len(games)}개 게임)")
    print(f"검토된 v5 게임 점수 반영: {imported['score_rows']}개 행 / {imported['matched_games']}개 게임")
    print(f"DB에 아직 없는 Steam AppID: {imported['missing_games']}개")


if __name__ == "__main__":
    main()
