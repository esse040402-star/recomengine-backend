"""새 프로토타입의 계정 기능 API.  프론트 규격: /api/account/{session,signup,login,logout,state}
- 성공: JSON, 실패: 상태코드 + {"error": "사용자에게 보여줄 한국어 메시지"} (main.py 의 예외 핸들러가 보장)
- 로그인 상태는 서명된 HttpOnly 쿠키로 유지 (프론트는 쿠키를 자동으로 보냄 → 같은 서버에서 서빙해야 함)"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import docs, session_cookie
from app.auth import session_secret, session_user
from app.config import get_settings
from app.db import get_supabase, run
from app.services import accounts, throttle

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/account", tags=[docs.ACCOUNT])

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
MAX_STATE_BYTES = 1_000_000


class SignupIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "지헌", "email": "user@example.com", "password": "password1234"}]})
    name: str = Field(min_length=1, max_length=24, description="닉네임 (1~24자)")
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN, description="이메일 (로그인 아이디)")
    password: str = Field(min_length=8, max_length=128, description="비밀번호 (8자 이상)")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해 주세요.")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()


class LoginIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"email": "user@example.com", "password": "password1234"}]})
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN, description="가입한 이메일")
    password: str = Field(min_length=1, max_length=128, description="비밀번호")

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()


class StateIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"state": {"track": "gamer", "liked": ["elden"]}}]})
    state: dict[str, Any] = Field(description="저장할 화면 상태 전체 (JSON, 1MB 이하)")


def _public(user: dict) -> dict:
    """프론트에 돌려줄 사용자 정보. 프로필 화면이 accountUser.email 을 보여준다."""
    return {"id": user["id"], "name": user.get("name") or "사용자", "email": user.get("email") or ""}


def _start_session(response: Response, user: dict) -> None:
    s = get_settings()
    ttl = s.session_days * 86400
    # 이메일도 쿠키에 담아 새로고침(GET /session) 때 DB 조회 없이 돌려준다. 예전 쿠키에는 없어서 빈 글자가 된다
    token = session_cookie.sign({"uid": user["id"], "name": user["name"], "email": user.get("email", "")}, session_secret(), ttl)
    response.set_cookie(session_cookie.COOKIE_NAME, token, max_age=ttl, httponly=True,
                        samesite="lax", secure=s.cookie_secure, path="/")


async def _load_state(uid: str) -> dict | None:
    try:
        res = await run(lambda: get_supabase().table("user_states").select("state").eq("user_id", uid).limit(1).execute())
    except Exception as exc:
        log.warning("user_states 조회 실패(테이블이 없을 수 있음): %s", type(exc).__name__)
        return None
    return res.data[0]["state"] if res.data else None


def _fail(exc: accounts.AccountError) -> HTTPException:
    return HTTPException(exc.status, exc.message)


@router.get("/session", **docs.doc("account_session"))
async def get_session(request: Request):
    user = session_user(request)
    if not user:
        return {"user": None}
    out: dict = {"user": _public({**user, "id": user["uid"]})}
    state = await _load_state(user["uid"])
    if state:
        out["state"] = state
    return out


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


@router.post("/signup", status_code=201, **docs.doc("account_signup"))
async def signup(body: SignupIn, request: Request, response: Response):
    key = f"signup|{_client_ip(request)}"
    try:
        throttle.check(key, limit=throttle.SIGNUP_MAX, window=throttle.SIGNUP_WINDOW_SECONDS)
    except throttle.TooManyAttempts:
        raise HTTPException(429, "가입 시도가 너무 많아요. 잠시 후 다시 시도해 주세요.")
    throttle.fail(key)  # 성공·실패와 관계없이 시도 횟수로 센다
    try:
        user = await accounts.create_account(body.name, body.email, body.password)
    except accounts.AccountError as exc:
        raise _fail(exc)
    _start_session(response, user)
    return {"user": _public(user)}  # state 없음 -> 프론트가 현재 게스트 상태를 그대로 사용


@router.post("/login", **docs.doc("account_login"))
async def login(body: LoginIn, request: Request, response: Response):
    key = f"{_client_ip(request)}|{body.email}"
    try:
        throttle.check(key)
    except throttle.TooManyAttempts:
        raise HTTPException(429, "로그인 시도가 너무 많아요. 잠시 후 다시 시도해 주세요.")
    try:
        user = await accounts.verify_login(body.email, body.password)
    except accounts.AccountError as exc:
        if exc.status == 401:
            throttle.fail(key)
        raise _fail(exc)
    throttle.clear(key)
    _start_session(response, user)
    out: dict = {"user": _public(user)}
    state = await _load_state(user["id"])
    if state:
        out["state"] = state
    return out


@router.post("/logout", **docs.doc("account_logout"))
async def logout(response: Response):
    response.delete_cookie(session_cookie.COOKIE_NAME, path="/")
    return {"ok": True}


@router.put("/state", **docs.doc("account_state"))
async def save_state(body: StateIn, request: Request):
    user = session_user(request)
    if not user:
        raise HTTPException(401, "로그인이 필요해요.")
    if len(json.dumps(body.state, ensure_ascii=False)) > MAX_STATE_BYTES:
        raise HTTPException(413, "저장할 데이터가 너무 커요.")
    row = {"user_id": user["uid"], "state": body.state, "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        await run(lambda: get_supabase().table("user_states").upsert(row, on_conflict="user_id").execute())
    except Exception as exc:
        log.warning("계정 상태 저장 실패: %s", type(exc).__name__)
        raise HTTPException(503, "계정 저장소에 저장하지 못했어요.")
    return {"ok": True}
