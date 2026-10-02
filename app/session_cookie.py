"""서명된 로그인 세션 쿠키 (표준 라이브러리만 사용).  형식: v1.<payload>.<HMAC-SHA256 서명>"""
import base64
import hashlib
import hmac
import json
import time

COOKIE_NAME = "recom_session"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sig(payload: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def sign(data: dict, secret: str, ttl_seconds: int, now: float | None = None) -> str:
    body = {**data, "exp": int((now if now is not None else time.time()) + ttl_seconds)}
    payload = _b64(json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode())
    return f"v1.{payload}.{_sig(payload, secret)}"


def verify(token: str | None, secret: str, now: float | None = None) -> dict | None:
    """유효하면 payload(dict), 위조/만료/형식 오류면 None."""
    try:
        version, payload, sig = (token or "").split(".")
        if version != "v1" or not hmac.compare_digest(sig, _sig(payload, secret)):
            return None
        data = json.loads(_unb64(payload))
        if not isinstance(data, dict) or data.get("exp", 0) < (now if now is not None else time.time()):
            return None
        return data if isinstance(data.get("uid"), str) and data["uid"] else None
    except Exception:
        return None
