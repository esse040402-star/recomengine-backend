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
        if "친절한 게임 추천 상담 AI" in system:
            return {"ready": True, "reply": "조건에 맞는 게임을 찾아봤어요.", "search_query": "스토리 중심 PC 싱글 플레이 게임"}
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












def test_chat_recommendation_returns_five_or_fewer_real_games(client):
    response = client.post("/api/ai/chat-recommendation", json={
        "message": "스토리 중심이고 PC에서 할 수 있는 게임을 추천해줘",
        "history": [{"role": "user", "content": "혼자 할 게임을 찾고 있어"}],
        "profile_context": {"title": "이야기에 빠지는 감상가", "axes": [30, 40, 50, 90, 60, 20],
                            "prefs": {"platforms": ["pc"], "avoid": []}},
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True and data["reply"]
    assert len(data["results"]) <= 5
    assert all(any(p.lower() in (" ".join(item["game"].get("platforms") or [])).lower() for p in ("pc", "windows", "linux", "playstation", "xbox", "nintendo")) for item in data["results"])



def test_chat_conversation_mode_uses_external_render_candidates(client, monkeypatch):
    from app.routers import ai as ai_router
    from app.services import ai_features

    captured_prompt = {}
    async def capture_chat(system, user, temperature=0.4, max_tokens=None):
        if "친절한 게임 추천 상담 AI" in system:
            captured_prompt.update(json.loads(user))
            return {"ready": True, "reply": "조건을 확인했어요.", "search_query": "PC 어드벤처 스토리 게임", "candidate_titles": ["External Story Quest"]}
        return {"text": "스토리 취향에 잘 맞는 게임이에요."}

    searched_titles = []
    async def external_search(query, page=1, size=20):
        searched_titles.append(query)
        return {"items": [{
            "id": "steam-987654", "appid": 987654, "title": "External Story Quest",
            "platforms": ["Xbox"], "genres": ["Adventure"], "tags": ["Story Rich", "Horror"],
            "cover_url": "https://example.com/cover.jpg", "source": "external"
        }]}

    async def parse_intent(query, vocab, games):
        assert any(g.get("id") == "steam-987654" for g in games)
        return {"liked_games": [], "genres": ["Adventure"], "tags": ["Story Rich"],
                "platforms": [], "exclude_platforms": [], "prefer": {}, "source": "test"}

    monkeypatch.setattr(ai_router.external_games, "search_external_games", external_search)
    monkeypatch.setattr(ai_features, "parse_search_intent", parse_intent)
    monkeypatch.setattr(ai_router, "_shape_results", lambda found, context, explain, top_n=3: __import__('asyncio').sleep(0, result=[
        {"game": ai_features.public_game(x["game"]), "score": x["score"], "matched": x["matched"], "reason": "테스트 추천", "reason_source": "rule"}
        for x in found
    ]))
    monkeypatch.setattr(ai_router.ollama if hasattr(ai_router, 'ollama') else __import__('app.services.ollama', fromlist=['chat_json']), "chat_json", capture_chat, raising=False)
    response = client.post("/api/ai/chat-recommendation", json={
        "message": "스토리가 좋은 게임 추천해줘", "mode": "conversation",
        "profile_context": {"axes": [0, 0, 0, 100, 0, 0], "prefs": {"platforms": ["pc"], "avoid": ["horror"]}}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "conversation"
    assert captured_prompt["saved_profile"] is None
    assert searched_titles == ["External Story Quest"]
    assert any(item["game"]["id"] == "steam-987654" for item in data["results"])


def test_chat_profile_mode_loads_saved_game_trait_vectors(client, monkeypatch):
    from app.routers import ai as ai_router
    from app.services import ai_features

    async def capture_chat(system, user, temperature=0.4, max_tokens=None):
        if "친절한 게임 추천 상담 AI" in system:
            return {"ready": True, "reply": "확인했어요.", "search_query": "스토리 PC 게임"}
        return {"text": "추천 이유입니다."}

    async def no_external(*args, **kwargs):
        return {"items": []}

    async def parse_intent(query, vocab, games):
        return {"liked_games": [], "genres": [], "tags": [], "platforms": [], "exclude_platforms": [], "prefer": {}, "source": "test"}

    candidate = {"id": "test-game-id", "title": "Trait Vector Test", "platforms": ["PC"],
                 "genres": ["Adventure"], "tags": ["Story Rich"], "cover_url": None}
    def fake_search_games(*args, **kwargs):
        return [{"game": candidate, "score": 50.0, "matched": ["Story Rich"]}]

    async def fake_vectors(game_ids):
        return {game_id: {"vector": [50, 50, 50, 95, 50, 50], "matched_tags": ["Story Rich"]} for game_id in game_ids}

    called = {"ids": None, "score": None}
    async def record_vectors(game_ids):
        called["ids"] = list(game_ids)
        return await fake_vectors(game_ids)

    async def capture_results(found, context, explain, top_n=3):
        called["score"] = found[0]["score"] if found else None
        return []

    monkeypatch.setattr(ai_router.external_games, "search_external_games", no_external)
    monkeypatch.setattr(ai_features, "parse_search_intent", parse_intent)
    monkeypatch.setattr(ai_features, "search_games", fake_search_games)
    monkeypatch.setattr(ai_router.trait_engine, "load_game_trait_vectors_async", record_vectors)
    monkeypatch.setattr(ai_router, "_shape_results", capture_results)
    monkeypatch.setattr(__import__('app.services.ollama', fromlist=['chat_json']), "chat_json", capture_chat)
    response = client.post("/api/ai/chat-recommendation", json={
        "message": "스토리 게임 추천해줘", "mode": "profile",
        "profile_context": {"axes": [50, 50, 50, 95, 50, 50], "prefs": {"platforms": ["pc"], "avoid": []}}
    })
    assert response.status_code == 200
    assert response.json()["mode"] == "profile"
    assert called["ids"] == ["test-game-id"]
    assert called["score"] == 62.5


def test_chat_asks_one_question_when_user_has_not_given_enough_preferences(client, monkeypatch):
    async def needs_more_info(system, user, temperature=0.4, max_tokens=None):
        return {"ready": False, "reply": "주로 PC와 콘솔 중 어떤 기기에서 플레이하시나요?", "search_query": ""}

    async def external_should_not_be_called(*args, **kwargs):
        raise AssertionError("조건이 부족한 단계에서는 Render 검색을 시작하면 안 됩니다.")

    monkeypatch.setattr(ollama, "chat_json", needs_more_info)
    from app.routers import ai as ai_router
    monkeypatch.setattr(ai_router.external_games, "search_external_games", external_should_not_be_called)
    response = client.post("/api/ai/chat-recommendation", json={
        "message": "게임 추천해줘", "mode": "conversation"
    })
    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["results"] == []
    assert "어떤 기기" in response.json()["reply"]
