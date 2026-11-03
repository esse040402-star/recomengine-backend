from app.db import get_supabase, run
from app.services.paging import collect_pages


async def load_all_games(columns: str) -> list[dict]:
    """games 테이블 전체를 1000행씩 나눠 읽는다 (Supabase는 한 번에 1000행까지만 돌려줌)."""
    def fetch(start: int, end: int) -> list[dict]:
        return get_supabase().table("games").select(columns).order("id").range(start, end).execute().data

    return await run(lambda: collect_pages(fetch))
