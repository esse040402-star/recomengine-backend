from app.mock_db import MockSupabase
from app.services import trait_engine
from app.services.recommender import recommend


def test_answer_indexes_accepts_only_unique_non_negative_integer_values():
    assert trait_engine._answer_indexes(["0", 1, "1", -1, "bad", None]) == [0, 1]
    assert trait_engine._answer_indexes({"selected": [0]}) == []


def test_calculate_session_scores_reads_option_trait_scores_and_persists(monkeypatch):
    sb = MockSupabase(seed=False)
    sb.tables["diagnosis_answers"] = [
        {"session_id": "session-1", "question_id": "G_ONB_03", "answer": ["0", "1"]}
    ]
    sb.tables["survey_options"] = [
        {"option_id": "option-0", "question_id": "G_ONB_03", "option_order": 0},
        {"option_id": "option-1", "question_id": "G_ONB_03", "option_order": 1},
    ]
    sb.tables["taste_traits"] = [
        {"trait_id": "trait-physical", "trait_name": "physical"},
        {"trait_id": "trait-strategy", "trait_name": "strategy"},
    ]
    sb.tables["option_trait_scores"] = [
        {"option_id": "option-0", "trait_id": "trait-physical", "base_weight": 90},
        {"option_id": "option-1", "trait_id": "trait-strategy", "base_weight": 80},
    ]
    monkeypatch.setattr(trait_engine, "get_supabase", lambda: sb)

    result = trait_engine.calculate_session_scores("session-1")

    assert result["mapped_questions"] == 1
    assert result["scores"]["physical"] == 90
    assert result["scores"]["strategy"] == 80
    assert result["scores"]["comfort"] == 50
    saved = sb.tables["survey_trait_scores"]
    assert {row["trait_id"] for row in saved} == {"trait-physical", "trait-strategy"}


def test_recommender_prefers_persisted_game_trait_vectors():
    games = [
        {"id": "game-db-fit", "title": "Fit", "genres": ["action"], "tags": [], "platforms": ["PC"]},
        {"id": "game-db-miss", "title": "Miss", "genres": ["action"], "tags": [], "platforms": ["PC"]},
    ]
    vectors = {
        "game-db-fit": {"vector": [90, 50, 50, 50, 50, 50], "matched_tags": ["action"]},
        "game-db-miss": {"vector": [10, 50, 50, 50, 50, 50], "matched_tags": ["action"]},
    }
    rows = recommend([90, 50, 50, 50, 50, 50], games, {}, game_trait_vectors=vectors)

    assert rows[0]["game_id"] == "game-db-fit"
    assert rows[0]["algorithm_version"] == "trait-db-v2"


def test_refresh_game_traits_uses_normalized_tag_rules(monkeypatch):
    sb = MockSupabase(seed=False)
    sb.tables["game_trait_tag_rules"] = [
        {"normalized_tag_name": "action", "trait_id": "trait-physical", "weight": 80},
        {"normalized_tag_name": "open world", "trait_id": "trait-exploration", "weight": 95},
    ]
    monkeypatch.setattr(trait_engine, "get_supabase", lambda: sb)

    count = trait_engine.refresh_game_traits_many([
        {"id": "game-1", "genres": ["Action"], "tags": ["Open World"]}
    ])

    assert count == 2
    saved = {row["trait_id"]: row["trait_score"] for row in sb.tables["game_trait_scores"]}
    assert saved == {"trait-physical": 80.0, "trait-exploration": 95.0}
