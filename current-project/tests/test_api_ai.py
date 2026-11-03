"""AI API 통합 테스트 (mock DB + 가짜 Ollama).  pytest 로 실행 (fastapi, httpx 필요)."""
import json
import os

os.environ["USE_MOCK_DB"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ollama


def fake_chat_json(system, user, temperature=0.4, max_tokens=None):
    async def run():
        if "검색어 분석기" in system:
            return {"liked_games": ["Animal Crossing: New Horizons"], "exclude_platforms": ["switch"]}
        if "추천 이유" in system:
            title = json.loads(user)["game"]["title"]  # 새 검증: 문장에 [게임 제목] 이 있어야 AI 문장으로 인정
            return {"text": f"퇴근 후 편하게 쉬고 싶은 분께 [{title}]을(를) 추천해요. 부담 없이 즐기기 좋아요."}
        if "라이브러리" in system:
            return {"pick": 0, "reason": "짧게 즐기기 좋아서 지금 기분에 잘 맞아요."}
        if "일정" in system:
            return {"text": "주말에 2시간씩 하면 엔딩까지 약 15주가 걸려요. 더 짧은 게임부터 시작해 보세요."}
        if "리뷰" in system:
            return {"pros": ["전투가 재미있다"], "cons": ["최적화 아쉬움"], "verdict": "전반적으로 호평"}
        raise RuntimeError("처리하지 않는 프롬프트")
    return run()


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(ollama, "chat_json", fake_chat_json)
    with TestClient(app) as c:
        yield c


def game_id(client, q):
    return client.get("/api/games", params={"q": q}).json()["items"][0]["id"]


def test_search_alternative(client):
    r = client.post("/api/ai/search", json={"query": "스위치 없는데 동물의 숲 같은 게임 없어?"}).json()
    names = [x["game"]["title"] for x in r["results"]]
    assert r["liked_games"] == ["Animal Crossing: New Horizons"] and "Stardew Valley" in names[:3]
    assert r["results"][0]["reason_source"] == "ollama"


def test_search_alias_works_even_when_llm_misses_the_game(client, monkeypatch):
    async def llm_without_liked(*a, **k):
        return {"liked_games": [], "genres": ["Puzzle"], "tags": [], "prefer": {"cheap": True}}
    monkeypatch.setattr(ollama, "chat_json", llm_without_liked)
    r = client.post("/api/ai/search", json={"query": "스위치 없는데 동물의 숲 같은 게임 없어?", "explain": False}).json()
    assert r["liked_games"] == ["Animal Crossing: New Horizons"]
    assert not any(r["intent"]["prefer"].values())                     # AI가 지어낸 cheap 은 무시
    assert not any("할인 중" in x["matched"] for x in r["results"])
    assert "Resident Evil Village" not in [x["game"]["title"] for x in r["results"]]
    assert all(x["reason_source"] == "rule" for x in r["results"])      # explain=false


def test_search_falls_back_when_ollama_fails(client, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(ollama, "chat_json", boom)
    r = client.post("/api/ai/search", json={"query": "친구랑 같이 할 힐링 게임"}).json()
    assert r["intent"]["source"] == "rule" and r["results"]
    assert all(x["reason_source"] == "rule" for x in r["results"])


def test_similar(client):
    r = client.post("/api/ai/similar", json={"titles": ["Elden Ring"], "prefer": ["cheap"]}).json()
    assert r["liked_games"] == ["Elden Ring"] and r["results"]
    assert client.post("/api/ai/similar", json={"titles": ["없는게임zzz"]}).status_code == 404


def test_schedule(client):
    r = client.post("/api/ai/schedule", json={"title": "Baldur's Gate 3", "text": "주말에 하루 2시간씩 쓸 수 있어"}).json()
    assert r["plan"]["weeks"] == 15.0 and r["shorter_alternatives"] and r["message_source"] == "ollama"
    assert client.post("/api/ai/schedule", json={"title": "Baldur's Gate 3"}).status_code == 422


def test_backlog(client):
    r = client.post("/api/ai/backlog", json={"games": ["Elden Ring", "Vampire Survivors", "내가모르는게임"],
                                              "mood": "머리 비우고 싶어", "minutes": 60}).json()
    assert r["pick"]["title"] and r["candidates_considered"] == 3 and r["matched_in_db"] == 2
    assert client.post("/api/ai/backlog", json={}).status_code == 422


def test_review_summary(client):
    gid = game_id(client, "Hades")
    reviews = ["전투가 정말 재미있어요", "후반부 최적화가 아쉬워요", "스토리와 연출이 훌륭합니다"]
    r = client.post("/api/ai/review-summary", json={"game_id": gid, "reviews": reviews}).json()
    assert r["pros"] and r["verdict"]
    assert client.post("/api/ai/review-summary", json={"game_id": gid}).status_code == 422  # steam_app_id 없음


def test_explain_and_deals_after_session(client):
    sid = client.post("/api/sessions", json={"track": "gamer"}).json()["id"]
    done = client.post(f"/api/sessions/{sid}/complete", json={"axes": [20, 60, 60, 60, 95, 10], "prefs": {}}).json()
    top = done["recommendations"][0]["games"]["id"]

    r = client.post("/api/ai/explain", json={"session_id": sid, "game_id": top}).json()
    assert r["source"] == "ollama"
    saved = client.get(f"/api/sessions/{sid}/result").json()["recommendations"][0]["reason"]
    assert saved == r["reason"]

    deals = client.get("/api/ai/deals", params={"session_id": sid}).json()
    assert deals["deals"] and deals["upcoming"]
    unfinished = client.post("/api/sessions", json={"track": "gamer"}).json()["id"]
    assert client.get("/api/ai/deals", params={"session_id": unfinished}).status_code == 409
