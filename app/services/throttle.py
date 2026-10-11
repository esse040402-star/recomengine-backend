"""시도 횟수 제한 (프로세스 메모리 기준: 서버를 재시작하면 초기화되고, 서버가 여러 대면 대수만큼 허용된다).
- 로그인: 같은 IP+이메일로 '실패'가 MAX_FAILURES 번 쌓이면 막는다
- 회원가입: 같은 IP에서 '시도'가 SIGNUP_MAX 번 쌓이면 막는다 (가짜 계정 대량 생성·가입 여부 떠보기 방지)"""
import time
from collections import deque

MAX_FAILURES = 8
WINDOW_SECONDS = 15 * 60
# 학교 와이파이처럼 여러 명이 같은 IP를 쓰는 시연 환경을 고려해 넉넉하게 잡는다
SIGNUP_MAX = 10
SIGNUP_WINDOW_SECONDS = 10 * 60
_failures: dict[str, deque] = {}


class TooManyAttempts(Exception):
    pass


def check(key: str, now: float | None = None, *, limit: int = MAX_FAILURES, window: float = WINDOW_SECONDS) -> None:
    now = time.time() if now is None else now
    q = _failures.get(key)
    if q is None:
        return
    while q and now - q[0] > window:
        q.popleft()
    if not q:
        _failures.pop(key, None)
    elif len(q) >= limit:
        raise TooManyAttempts()


def fail(key: str, now: float | None = None) -> None:
    _failures.setdefault(key, deque()).append(time.time() if now is None else now)


def clear(key: str) -> None:
    _failures.pop(key, None)
