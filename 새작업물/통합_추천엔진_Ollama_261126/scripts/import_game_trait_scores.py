"""Import the reviewed v5 six-axis game scores into Supabase game_trait_scores.

Run after seed_trait_model has created taste_traits and game rows:
    python -m scripts.import_game_trait_scores --dry-run
    python -m scripts.import_game_trait_scores

The input is keyed by Steam AppID; the script maps it to the existing games.id.
It never creates or changes games rows and never changes survey/profile answers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db import get_supabase
from app.services.recommender import AXES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "새작업물" / "게임취향_점수생성" / "개선_결과_v5" / "game_trait_scores_v5.json"


def chunks(items: list[Any], size: int = 200):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build_score_rows(
    document: dict[str, Any], game_ids_by_appid: dict[str, str], trait_ids: dict[str, str]
) -> tuple[list[dict], list[int], list[int]]:
    """Pure conversion helper; null axes are intentionally omitted, not set to 50."""
    rows: list[dict] = []
    missing_appids: list[int] = []
    matched_appids: list[int] = []
    for game in document.get("games") or []:
        appid = game.get("steam_app_id")
        if appid is None:
            continue
        appid_key = str(appid)
        game_id = game_ids_by_appid.get(appid_key)
        if not game_id:
            try:
                missing_appids.append(int(appid))
            except (TypeError, ValueError):
                pass
            continue
        matched_appids.append(int(appid))
        scores = game.get("scores") or {}
        evidence = game.get("score_evidence") or {}
        confidence = game.get("confidence") or {}
        evidence_count = game.get("evidence_count") or {}
        canonical_codes = game.get("canonical_codes") or []
        for axis in AXES:
            score = scores.get(axis)
            trait_id = trait_ids.get(axis)
            if score is None or trait_id is None:
                continue
            rows.append({
                "game_id": game_id,
                "trait_id": trait_id,
                "trait_score": float(score),
                "score_evidence": {
                    "matched_tags": canonical_codes,
                    "axis_evidence": evidence.get(axis) or [],
                    "confidence": confidence.get(axis),
                    "evidence_count": evidence_count.get(axis, 0),
                    "source_version": document.get("meta", {}).get("version", 5),
                },
            })
    return rows, missing_appids, matched_appids


def _all_game_ids(sb) -> dict[str, str]:
    result: dict[str, str] = {}
    start = 0
    page_size = 1000
    while True:
        batch = (
            sb.table("games")
            .select("id,steam_app_id")
            .range(start, start + page_size - 1)
            .execute()
            .data
            or []
        )
        for row in batch:
            if row.get("steam_app_id") is not None:
                result[str(row["steam_app_id"])] = str(row["id"])
        if len(batch) < page_size:
            break
        start += page_size
    return result


def import_game_trait_scores(sb=None, source: Path = DEFAULT_SOURCE, dry_run: bool = False) -> dict[str, int]:
    if not source.exists():
        raise FileNotFoundError(f"게임 점수 JSON을 찾을 수 없습니다: {source}")
    document = json.loads(source.read_text(encoding="utf-8"))
    expected = int((document.get("meta") or {}).get("game_count") or len(document.get("games") or []))
    actual = len(document.get("games") or [])
    if actual != expected:
        raise ValueError(f"게임 점수 파일 개수 불일치: meta={expected}, actual={actual}")

    sb = sb or get_supabase()
    game_ids_by_appid = _all_game_ids(sb)
    trait_rows = sb.table("taste_traits").select("trait_id,trait_name").execute().data or []
    trait_ids = {row["trait_name"]: str(row["trait_id"]) for row in trait_rows if row.get("trait_name") in AXES}
    missing_traits = [axis for axis in AXES if axis not in trait_ids]
    if missing_traits:
        raise RuntimeError(f"taste_traits에 취향 축이 없습니다: {', '.join(missing_traits)}")

    rows, missing_appids, matched_appids = build_score_rows(document, game_ids_by_appid, trait_ids)
    matched_game_ids = sorted({game_ids_by_appid[str(appid)] for appid in matched_appids})
    if dry_run:
        return {
            "source_games": actual,
            "matched_games": len(matched_game_ids),
            "missing_games": len(missing_appids),
            "score_rows": len(rows),
            "deleted_old_rows": 0,
        }

    deleted = 0
    for batch in chunks(matched_game_ids):
        sb.table("game_trait_scores").delete().in_("game_id", batch).execute()
        deleted += len(batch)
    for batch in chunks(rows):
        sb.table("game_trait_scores").upsert(batch, on_conflict="game_id,trait_id").execute()

    return {
        "source_games": actual,
        "matched_games": len(matched_game_ids),
        "missing_games": len(missing_appids),
        "score_rows": len(rows),
        "deleted_old_rows": deleted,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import reviewed v5 game trait scores into Supabase")
    parser.add_argument("--dry-run", action="store_true", help="DB 변경 없이 매핑 개수만 확인")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="게임 점수 JSON 경로")
    args = parser.parse_args()
    if get_settings().use_mock_db:
        raise SystemExit("USE_MOCK_DB=true 입니다. 실제 Supabase 연결(.env)을 설정하세요.")
    result = import_game_trait_scores(source=args.source, dry_run=args.dry_run)
    print("게임 성향 점수 가져오기 결과")
    for key, value in result.items():
        print(f"- {key}: {value}")
    if result["missing_games"]:
        print("- 참고: DB에 없는 Steam AppID는 건너뛰었습니다. games 테이블의 steam_app_id를 먼저 확인하세요.")


if __name__ == "__main__":
    main()
