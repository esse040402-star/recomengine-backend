"""mock DB 단위 테스트 (fastapi 불필요).  python -m tests.test_mock_db  또는 pytest"""
import json

from app.mock_db import SEED_FILE, MockSupabase


def fresh() -> MockSupabase:
    return MockSupabase(seed=True)


def test_seed_and_filters():
    db = fresh()
    res = db.table("games").select("id,title,genres", count="exact").execute()
    n = len(json.loads(SEED_FILE.read_text(encoding="utf-8")))
    assert res.count == n and len(res.data) == n
    assert set(res.data[0]) == {"id", "title", "genres"}

    q = db.table("games").select("title").ilike("title", "%elden%").execute()
    assert [r["title"] for r in q.data] == ["Elden Ring"]

    q = db.table("games").select("title").contains("genres", ["Puzzle"]).order("title").execute()
    assert [r["title"] for r in q.data] == ["Baba Is You", "Portal 2"]

    q = db.table("games").select("title", count="exact").order("title").range(0, 2).execute()
    assert len(q.data) == 3 and q.count == n


def test_session_defaults_and_upsert_and_delete():
    db = fresh()
    s = db.table("diagnosis_sessions").insert({"track": "gamer", "user_id": None}).execute().data[0]
    assert s["status"] == "in_progress" and s["id"] and s["started_at"]

    rows = [{"session_id": s["id"], "question_id": "q1", "answer": ["0"]}]
    db.table("diagnosis_answers").upsert(rows, on_conflict="session_id,question_id").execute()
    rows[0]["answer"] = ["1"]
    db.table("diagnosis_answers").upsert(rows, on_conflict="session_id,question_id").execute()
    got = db.table("diagnosis_answers").select("*").eq("session_id", s["id"]).execute().data
    assert len(got) == 1 and got[0]["answer"] == ["1"]

    db.table("diagnosis_sessions").update({"status": "completed"}).eq("id", s["id"]).execute()
    assert db.table("diagnosis_sessions").select("status").eq("id", s["id"]).execute().data[0]["status"] == "completed"

    db.table("diagnosis_answers").delete().eq("session_id", s["id"]).execute()
    assert db.table("diagnosis_answers").select("*").execute().data == []


def test_embedded_join_like_recommendations():
    db = fresh()
    game = db.table("games").select("id,title").eq("title", "Hades").execute().data[0]
    db.table("recommendations").insert(
        [{"session_id": "s1", "game_id": game["id"], "rank": 1, "match_score": 80}]
    ).execute()
    res = (
        db.table("recommendations")
        .select("rank,match_score,games(id,title,genres)")
        .eq("session_id", "s1")
        .order("rank")
        .execute()
    )
    assert res.data[0]["games"]["title"] == "Hades" and "genres" in res.data[0]["games"]


def test_mock_auth():
    db = fresh()
    assert db.auth.get_user("mock-alice").user.id == "alice"
    try:
        db.auth.get_user("real-jwt")
    except ValueError:
        return
    raise AssertionError("mock 토큰이 아니면 실패해야 함")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
