"""로그인 실패 횟수 제한 (프로세스 메모리 기준: 서버를 재시작하면 초기화되고, 서버가 여러 대면 대수만큼 허용된다)."""
import time
from collections import deque

MAX_FAILURES = 8
WINDOW_SECONDS = 15 * 60
_failures: dict[str, deque] = {}


class TooManyAttempts(Exception):
    pass


def check(key: str, now: float | None = None) -> None:
    now = time.time() if now is None else now
    q = _failures.get(key)
    if q is None:
        return
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if not q:
        _failures.pop(key, None)
    elif len(q) >= MAX_FAILURES:
        raise TooManyAttempts()


def fail(key: str, now: float | None = None) -> None:
    _failures.setdefault(key, deque()).append(time.time() if now is None else now)


def clear(key: str) -> None:
    _failures.pop(key, None)
