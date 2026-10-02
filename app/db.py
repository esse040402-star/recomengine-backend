from functools import lru_cache
from typing import Any, Callable, TypeVar

from starlette.concurrency import run_in_threadpool

from app.config import get_settings

T = TypeVar("T")


@lru_cache
def get_supabase() -> Any:
    s = get_settings()
    if s.use_mock_db:
        from app.mock_db import MockSupabase

        return MockSupabase()
    from supabase import create_client  # mock 모드에서는 supabase 패키지가 없어도 된다

    return create_client(s.supabase_url, s.supabase_service_key)


async def run(fn: Callable[[], T]) -> T:
    """supabase-py는 동기 클라이언트라서 스레드풀에서 실행해 이벤트 루프를 막지 않는다."""
    return await run_in_threadpool(fn)
