from scripts.import_game_trait_scores import build_score_rows


def test_build_score_rows_maps_by_steam_appid_and_preserves_null_axes():
    document = {
        "meta": {"version": 5},
        "games": [
            {
                "steam_app_id": 123,
                "scores": {"physical": 80, "strategy": None, "exploration": 70},
                "confidence": {"physical": "high", "exploration": "medium"},
                "evidence_count": {"physical": 3, "exploration": 2},
                "score_evidence": {"physical": [{"code": "genre:action"}], "exploration": []},
                "canonical_codes": ["genre:action", "tag:open_world"],
            },
            {"steam_app_id": 456, "scores": {"physical": 55}},
        ],
    }
    rows, missing, matched = build_score_rows(
        document,
        {"123": "game-uuid-123"},
        {"physical": "trait-physical", "strategy": "trait-strategy", "exploration": "trait-exploration"},
    )
    assert matched == [123]
    assert missing == [456]
    assert [(r["trait_id"], r["trait_score"]) for r in rows] == [
        ("trait-physical", 80.0),
        ("trait-exploration", 70.0),
    ]
    assert rows[0]["score_evidence"]["source_version"] == 5
    assert rows[0]["score_evidence"]["matched_tags"] == ["genre:action", "tag:open_world"]


def test_v5_score_dataset_has_unique_1284_appids_and_expected_rows():
    import json
    from scripts.import_game_trait_scores import DEFAULT_SOURCE
    from app.services.recommender import AXES

    document = json.loads(DEFAULT_SOURCE.read_text(encoding="utf-8"))
    appids = [str(game["steam_app_id"]) for game in document["games"]]
    assert len(appids) == 1284
    assert len(set(appids)) == 1284
    mapping = {appid: f"game-{appid}" for appid in appids}
    trait_ids = {axis: f"trait-{axis}" for axis in AXES}
    rows, missing, matched = build_score_rows(document, mapping, trait_ids)
    assert not missing and len(matched) == 1284
    assert len(rows) == 5265
