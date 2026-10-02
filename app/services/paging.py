"""Supabase(PostgREST)는 한 번에 최대 1000행만 돌려준다. 전체 행이 필요할 때 나눠서 끝까지 읽는다."""
from typing import Callable

PAGE_SIZE = 1000
MAX_ROWS = 20000


def collect_pages(fetch_page: Callable[[int, int], list[dict]], page_size: int = PAGE_SIZE, max_rows: int = MAX_ROWS) -> list[dict]:
    """fetch_page(start, end) -> 그 구간의 행 목록 (end 포함). 덜 찬 페이지가 나오면 끝."""
    out: list[dict] = []
    start = 0
    while start < max_rows:
        rows = fetch_page(start, min(start + page_size, max_rows) - 1)
        out.extend(rows)
        if len(rows) < page_size:
            break
        start += page_size
    return out
