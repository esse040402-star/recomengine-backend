import logging
import secrets

from fastapi import Header, HTTPException, Request

from app import session_cookie
from app.config import get_settings
from app.db import get_supabase, run

log = logging.getLogger(__name__)
_fallback_secret: str | None = None


def session_secret() -> str:
    global _fallback_secret
    configured = get_settings().session_secret
    if configured:
        return configured
    if _fallback_secret is None:
        _fallback_secret = secrets.token_urlsafe(32)
        log.warning("SESSION_SECRET 이 없어 임시 키를 만들었어요. 서버를 재시작하면 모두 로그아웃됩니다.")
    return _fallback_secret


def session_user(request: Request) -> dict | None:
    """로그인 쿠키가 유효하면 {'uid','name',...}, 아니면 None."""
    token = request.cookies.get(session_cookie.COOKIE_NAME)
    return session_cookie.verify(token, session_secret()) if token else None


async def optional_user_id(request: Request, authorization: str | None = Header(default=None, description="`Bearer <토큰>` 형식. 비워두면 로그인 쿠키 또는 비회원으로 처리. mock 모드에서는 `Bearer mock-이름`")) -> str | None:
    """1) Authorization: Bearer <Supabase 토큰> 이 있으면 검증, 2) 없으면 로그인 쿠키, 3) 둘 다 없으면 비회원(None).
    토큰이 있는데 잘못됐으면 401."""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(401, "Authorization 헤더 형식이 올바르지 않습니다.")
        try:
            res = await run(lambda: get_supabase().auth.get_user(token))
        except Exception:
            raise HTTPException(401, "유효하지 않은 토큰입니다.")
        if not res or not res.user:
            raise HTTPException(401, "유효하지 않은 토큰입니다.")
        return str(res.user.id)
    user = session_user(request)
    return user["uid"] if user else None


async def require_admin(x_admin_token: str | None = Header(default=None, description="관리자 토큰 (= .env 의 ADMIN_TOKEN)")) -> None:
    expected = get_settings().admin_token
    if not expected:
        raise HTTPException(403, "관리자 API가 비활성화되어 있습니다. .env에 ADMIN_TOKEN을 설정하세요.")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(403, "관리자 토큰이 올바르지 않습니다.")
