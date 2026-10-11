"""회원가입/로그인 (Supabase Auth 사용). 비밀번호는 Supabase가 해시해서 보관하며 이 서버는 저장하지 않는다."""
import logging

from app.config import get_settings
from app.db import get_supabase, run

log = logging.getLogger(__name__)


class AccountError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


# ---------- Supabase 오류 해석 ----------
def _is_duplicate(exc: Exception) -> bool:
    msg = str(exc).lower()
    return getattr(exc, "code", None) == "email_exists" or "already" in msg or "registered" in msg


def _is_invalid_credentials(exc: Exception) -> bool:
    msg = str(exc).lower()
    return getattr(exc, "status", None) in (400, 401, 422) or "invalid login" in msg or "invalid credentials" in msg


def user_dict(u) -> dict:
    meta = getattr(u, "user_metadata", None) or {}
    email = getattr(u, "email", "") or ""
    return {"id": str(u.id), "name": meta.get("name") or email.split("@")[0] or "사용자", "email": email}


def _login_client():
    """로그인 검증은 anon 키 클라이언트로 한다. 서비스 키 클라이언트로 로그인하면 그 클라이언트의
    권한이 사용자 토큰으로 바뀌어 버려서 서버 전체가 오동작할 수 있다."""
    s = get_settings()
    if s.use_mock_db:
        return get_supabase()
    if not s.supabase_anon_key:
        raise AccountError(503, "서버에 SUPABASE_ANON_KEY 가 설정되어 있지 않아 로그인할 수 없어요.")
    from supabase import create_client

    return create_client(s.supabase_url, s.supabase_anon_key)


async def create_account(name: str, email: str, password: str) -> dict:
    def work():
        return get_supabase().auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True, "user_metadata": {"name": name}}
        )

    try:
        res = await run(work)
    except Exception as exc:
        if _is_duplicate(exc):
            raise AccountError(409, "이미 가입된 이메일이에요. 로그인해 주세요.")
        log.warning("회원가입 실패: %s", type(exc).__name__)
        raise AccountError(502, "계정을 만들지 못했어요. 잠시 후 다시 시도해 주세요.")
    return user_dict(res.user)


async def verify_login(email: str, password: str) -> dict:
    client = _login_client()
    try:
        res = await run(lambda: client.auth.sign_in_with_password({"email": email, "password": password}))
    except Exception as exc:
        if _is_invalid_credentials(exc):
            raise AccountError(401, "이메일 또는 비밀번호가 올바르지 않아요.")
        log.warning("로그인 처리 실패: %s", type(exc).__name__)
        raise AccountError(502, "로그인 서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.")
    if not res or not res.user:
        raise AccountError(401, "이메일 또는 비밀번호가 올바르지 않아요.")
    return user_dict(res.user)
