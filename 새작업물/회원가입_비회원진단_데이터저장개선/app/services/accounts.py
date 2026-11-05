
"""회원가입/로그인 (Supabase Auth 사용)."""
import logging

from app.config import get_settings
from app.db import get_supabase, run

log = logging.getLogger(__name__)


class AccountError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _is_duplicate(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        getattr(exc, "code", None) == "email_exists"
        or "already" in msg
        or "registered" in msg
    )


def _is_email_not_confirmed(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "email_not_confirmed" in msg
        or "email not confirmed" in msg
    )


def _is_invalid_credentials(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "invalid login credentials" in msg
        or "invalid credentials" in msg
        or getattr(exc, "code", None) == "invalid_credentials"
    )


def user_dict(u) -> dict:
    meta = getattr(u, "user_metadata", None) or {}
    email = getattr(u, "email", "") or ""
    return {
        "id": str(u.id),
        "name": meta.get("name") or email.split("@")[0] or "사용자",
        "email": email,
    }


def _login_client():
    """로그인 검증은 anon 키 클라이언트로 처리한다."""
    s = get_settings()
    if s.use_mock_db:
        return get_supabase()
    if not s.supabase_anon_key:
        raise AccountError(
            503,
            "서버에 SUPABASE_ANON_KEY 가 설정되어 있지 않아 로그인할 수 없어요."
        )

    from supabase import create_client
    return create_client(s.supabase_url, s.supabase_anon_key)


async def create_account(name: str, email: str, password: str) -> tuple[dict | None, bool]:
    """
    첫 요청은 계정을 생성한다.
    인증 완료 후 다시 요청하면 기존 계정으로 로그인한다.
    반환값: (사용자 정보, 이메일 인증 필요 여부)
    """
    client = _login_client()

    # 먼저 기존 계정으로 로그인을 시도한다.
    try:
        login_res = await run(
            lambda: client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        )

        if login_res and login_res.user:
            return user_dict(login_res.user), False

    except Exception as exc:
        # 아직 이메일 인증을 하지 않은 계정
        if _is_email_not_confirmed(exc):
            return None, True

        # 로그인 정보가 맞지 않으면 신규 가입을 시도한다.
        if not _is_invalid_credentials(exc):
            log.warning("회원가입 전 로그인 확인 실패: %s", type(exc).__name__)
            raise AccountError(
                502,
                "계정 서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요."
            )

    # 기존 계정 로그인이 안 되면 신규 가입을 시도한다.
    try:
        signup_res = await run(
            lambda: client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {"name": name}
                }
            })
        )
    except Exception as exc:
        if _is_duplicate(exc):
            raise AccountError(
                401,
                "이미 가입된 이메일이에요. 이메일과 비밀번호를 확인해 주세요."
            )
        log.exception("회원가입 실패")
        raise AccountError(
            502,
            "계정을 만들지 못했어요. 잠시 후 다시 시도해 주세요."
        )

    if not signup_res or not signup_res.user:
        raise AccountError(502, "회원가입 응답을 확인할 수 없어요.")

    # Supabase는 이미 존재하는 이메일에 대해 identities가 빈 사용자로
    # 응답할 수 있다. 이 경우 새 계정으로 취급하지 않는다.
    identities = getattr(signup_res.user, "identities", None)
    if identities is not None and len(identities) == 0:
        raise AccountError(
            401,
            "이미 가입된 이메일이에요. 이메일과 비밀번호를 확인해 주세요."
        )

    return user_dict(signup_res.user), signup_res.session is None


async def verify_login(email: str, password: str) -> dict:
    client = _login_client()

    try:
        res = await run(
            lambda: client.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        )
    except Exception as exc:
        if _is_email_not_confirmed(exc):
            raise AccountError(403, "이메일 인증을 먼저 완료해 주세요.")
        if _is_invalid_credentials(exc):
            raise AccountError(401, "이메일 또는 비밀번호가 올바르지 않아요.")

        log.warning("로그인 처리 실패: %s", type(exc).__name__)
        raise AccountError(
            502,
            "로그인 서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요."
        )

    if not res or not res.user:
        raise AccountError(401, "이메일 또는 비밀번호가 올바르지 않아요.")

    return user_dict(res.user)
