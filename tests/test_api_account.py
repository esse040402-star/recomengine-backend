"""계정 API / 에러 형식 / 설문 생성 통합 테스트 (mock DB + 가짜 Ollama).  pytest 로 실행 (fastapi, httpx 필요)."""
import json
import os
from pathlib import Path

os.environ["USE_MOCK_DB"] = "true"
os.environ.setdefault("SESSION_SECRET", "test-session-secret-1234567890")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ollama, throttle

BLUEPRINT = json.loads((Path(__file__).parent / "fixtures" / "blueprints.json").read_text(encoding="utf-8"))["gamer"]["blueprint"]
SIGNUP = {"name": "지헌", "email": "Jiheon@Example.com", "password": "pw-12345678"}


@pytest.fixture()
def client():
    throttle._failures.clear()
    with TestClient(app) as c:
        yield c


def test_signup_session_state_logout_flow(client):
    assert client.get("/api/account/session").json() == {"user": None}

    r = client.post("/api/account/signup", json=SIGNUP)
    assert r.status_code == 201 and r.json()["user"]["name"] == "지헌" and "state" not in r.json()
    assert r.json()["user"]["email"] == "jiheon@example.com"  # 프로필 화면이 accountUser.email 을 보여준다
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "password" not in r.text

    me = client.get("/api/account/session").json()
    assert me["user"]["name"] == "지헌" and "state" not in me
    assert me["user"]["email"] == "jiheon@example.com"  # 새로고침 뒤에도 이메일 유지 (쿠키에 담김)

    saved = {"track": "gamer", "quick": {"completed": True, "answers": {"q1": ["0"]}}, "liked": ["elden"]}
    assert client.put("/api/account/state", json={"state": saved}).json() == {"ok": True}
    assert client.get("/api/account/session").json()["state"] == saved

    assert client.post("/api/account/logout").json() == {"ok": True}
    assert client.get("/api/account/session").json() == {"user": None}
    assert client.put("/api/account/state", json={"state": saved}).status_code == 401

    # 같은 이메일(대소문자 무관)로 다시 로그인하면 저장한 상태가 돌아온다
    r = client.post("/api/account/login", json={"email": "jiheon@example.com", "password": "pw-12345678"})
    assert r.status_code == 200 and r.json()["state"] == saved
    assert r.json()["user"]["email"] == "jiheon@example.com"


def test_old_cookie_without_email_still_works(client):
    """이메일을 넣기 전에 발급된 쿠키도 로그인 상태로 인정하고, 이메일은 빈 글자로 돌려준다."""
    from app import session_cookie
    from app.auth import session_secret
    client.cookies.set(session_cookie.COOKIE_NAME, session_cookie.sign({"uid": "old-user", "name": "예전"}, session_secret(), 600))
    me = client.get("/api/account/session").json()
    assert me["user"] == {"id": "old-user", "name": "예전", "email": ""}


def test_signup_throttle(client):
    codes = [client.post("/api/account/signup", json={**SIGNUP, "email": f"spam{i}@example.com"}).status_code
             for i in range(throttle.SIGNUP_MAX + 1)]
    assert set(codes[:-1]) == {201} and codes[-1] == 429
    assert "가입 시도" in client.post("/api/account/signup", json={**SIGNUP, "email": "late@example.com"}).json()["error"]


def test_real_db_mode_requires_session_secret():
    """실제 DB 모드에서 SESSION_SECRET 이 없으면 서버가 시작되지 않아야 한다 (임시 키로 로그인이 풀리는 것 방지)."""
    from pydantic import ValidationError
    from app.config import Settings
    real = {"_env_file": None, "use_mock_db": False, "supabase_url": "https://example.supabase.co", "supabase_service_key": "k"}
    with pytest.raises(ValidationError, match="SESSION_SECRET"):
        Settings(**real, session_secret="")
    assert Settings(**real, session_secret="x" * 32).session_secret
    assert Settings(_env_file=None, use_mock_db=True, session_secret="").use_mock_db  # 가짜 DB 모드는 임시 키 허용


def test_error_shape_is_error_key(client):
    client.post("/api/account/signup", json=SIGNUP)
    dup = client.post("/api/account/signup", json={**SIGNUP, "email": "jiheon@example.com"})
    assert dup.status_code == 409 and "이미 가입" in dup.json()["error"]

    bad = client.post("/api/account/login", json={"email": "jiheon@example.com", "password": "wrong-password"})
    assert bad.status_code == 401 and "올바르지" in bad.json()["error"]
    unknown = client.post("/api/account/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert unknown.json()["error"] == bad.json()["error"]  # 계정 존재 여부를 알려주지 않음

    short = client.post("/api/account/signup", json={**SIGNUP, "email": "x@example.com", "password": "pw1234"})
    assert short.status_code == 422 and isinstance(short.json()["error"], str)
    assert "pw1234" not in short.text  # 입력한 비밀번호가 응답에 되돌아오면 안 됨

    assert isinstance(client.get("/api/games/00000000-0000-0000-0000-000000000000").json()["error"], str)


def test_login_throttle(client):
    client.post("/api/account/signup", json=SIGNUP)
    body = {"email": "jiheon@example.com", "password": "wrong-password"}
    codes = [client.post("/api/account/login", json=body).status_code for _ in range(throttle.MAX_FAILURES + 1)]
    assert codes[-1] == 429 and set(codes[:-1]) == {401}
    # 제한에 걸린 동안에는 올바른 비밀번호도 거부
    assert client.post("/api/account/login", json={**body, "password": "pw-12345678"}).status_code == 429


def test_state_size_limit(client):
    client.post("/api/account/signup", json={**SIGNUP, "email": "big@example.com"})
    huge = {"blob": "가" * 1_100_000}
    assert client.put("/api/account/state", json={"state": huge}).status_code == 413


def test_cookie_login_works_for_diagnosis_session(client):
    client.post("/api/account/signup", json={**SIGNUP, "email": "own@example.com"})
    sid = client.post("/api/sessions", json={"track": "gamer"}).json()["id"]
    assert client.get(f"/api/sessions/{sid}/result").status_code == 200
    client.post("/api/account/logout")
    assert client.get(f"/api/sessions/{sid}/result").status_code == 403  # 로그인 사용자의 세션은 본인만


def _fake_chat(system, user, temperature=0.4, max_tokens=None):
    async def run():
        data = json.loads(user)
        return {"questions": [
            {"id": q["id"], "title": f"{q['title'][:60]} (다듬음 {q['id']})",
             "options": [{"id": o["id"], "label": f"{o['label'][:40]} 다듬음"} for o in q["options"]]}
            for q in data["questions"]]}
    return run()


def test_survey_generate_new_request_shape(client, monkeypatch):
    monkeypatch.setattr(ollama, "chat_json", _fake_chat)
    body = {"track": "gamer", "answers": {"q1": ["0"]}, "request": "혼자 편하게 즐길 무료 게임",
            "profileContext": {"axes": [90, 50, 60, 60, 15, 70], "prefs": {"avoid": ["horror"]}},
            "blueprint": BLUEPRINT}
    r = client.post("/api/survey/generate", json=body)
    assert r.status_code == 200 and len(r.json()["questions"]) == 28 and r.json()["rewritten"] == 28
    missing = client.post("/api/survey/generate", json={k: v for k, v in body.items() if k != "blueprint"})
    assert missing.status_code == 422 and "blueprint" in missing.json()["error"]


def test_status_reports_mock_and_ai(client, monkeypatch):
    async def none():
        return None
    monkeypatch.setattr(ollama, "list_models", none)
    body = client.get("/api/status").json()
    assert body["ai"] is False and body["ollama"]["up"] is False and body["mock_db"] is True


def test_status_fast_when_ollama_hangs(client, monkeypatch):
    """Ollama가 멈춰 응답이 없어도 /api/status 는 프론트 제한(2.5초) 안에 feeds=true 를 돌려줘야 한다."""
    import asyncio
    import time

    async def hang():
        await asyncio.sleep(10)
    monkeypatch.setattr(ollama, "_fetch_models", hang)
    started = time.monotonic()
    body = client.get("/api/status").json()
    assert time.monotonic() - started < 2.0
    assert body["feeds"] is True and body["ai"] is False
