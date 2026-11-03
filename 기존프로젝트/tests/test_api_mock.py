"""mock 모드 API 통합 테스트.  pytest 로 실행 (fastapi, httpx 필요)."""
import os

os.environ["USE_MOCK_DB"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_status(client):
    body = client.get("/api/status").json()
    assert body["mock_db"] is True and body["feeds"] is True


def test_games(client):
    data = client.get("/api/games", params={"q": "hades"}).json()
    assert data["total"] == 1
    gid = data["items"][0]["id"]
    assert client.get(f"/api/games/{gid}").json()["title"] == "Hades"
    assert client.get("/api/games/00000000-0000-0000-0000-000000000000").status_code == 404


def test_full_session_flow(client):
    sid = client.post("/api/sessions", json={"track": "gamer"}).json()["id"]

    r = client.put(f"/api/sessions/{sid}/answers", json={"answers": [{"question_id": "q1", "answer": ["0"]}]})
    assert r.status_code == 200 and r.json()["saved"] == 1

    body = {
        "axes": [90, 50, 60, 60, 15, 70],
        "title": "손맛을 즐기는 도전자",
        "prefs": {"platforms": ["pc"], "avoid": ["horror"]},
        "evidence": [{"question": "q", "answer": "a"}],
    }
    result = client.post(f"/api/sessions/{sid}/complete", json=body).json()
    assert result["session"]["status"] == "completed"
    assert result["scores"]["physical"] == 90
    assert result["report"]["generated_by"] in ("ollama", "rule")
    recs = result["recommendations"]
    assert recs and recs[0]["rank"] == 1 and recs[0]["games"]["title"]
    assert "Resident Evil Village" not in [r["games"]["title"] for r in recs]  # horror 회피

    assert client.get(f"/api/sessions/{sid}/result").json()["recommendations"]
    # 완료된 세션에는 답변 저장 불가
    r = client.put(f"/api/sessions/{sid}/answers", json={"answers": [{"question_id": "q2", "answer": ["0"]}]})
    assert r.status_code == 409


def test_session_ownership(client):
    sid = client.post("/api/sessions", json={"track": "nongamer"}, headers={"Authorization": "Bearer mock-alice"}).json()["id"]
    assert client.get(f"/api/sessions/{sid}/result").status_code == 403
    assert client.get(f"/api/sessions/{sid}/result", headers={"Authorization": "Bearer mock-bob"}).status_code == 403
    assert client.get(f"/api/sessions/{sid}/result", headers={"Authorization": "Bearer mock-alice"}).status_code == 200
    assert client.get(f"/api/sessions/{sid}/result", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_survey_generate_needs_blueprint(client):
    assert client.post("/api/survey/generate", json={"track": "gamer", "answers": {}}).status_code == 422
