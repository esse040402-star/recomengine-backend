"""한국어 게임 이름 -> 영어 공식 제목 (data/game_aliases.json).
LLM(Ollama)이 '동물의 숲'을 'Animal Crossing'으로 바꾸지 못하는 경우가 있어서, 코드가 먼저 확실하게 처리한다."""
import json
import re
from functools import lru_cache
from pathlib import Path

ALIAS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "game_aliases.json"
MIN_KEY_LEN = 3  # 정규화한 별칭이 2글자 이하면 다른 단어 속에 섞여 오탐이 많아서 무시 (예: '롤' in '컨트롤')


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", (s or "").lower())


@lru_cache
def _table() -> tuple[tuple[str, str], ...]:
    raw = json.loads(ALIAS_FILE.read_text(encoding="utf-8")) if ALIAS_FILE.exists() else {}
    items = [(_norm(k), v) for k, v in raw.items() if not k.startswith("_") and isinstance(v, str) and _norm(k)]
    return tuple(sorted(items, key=lambda kv: -len(kv[0])))  # 긴 별칭부터 (예: '발더스 게이트 3' > '발더스 게이트')


def canonical(title: str) -> str:
    """제목이 별칭표와 정확히 일치하면 영어 제목, 아니면 그대로."""
    n = _norm(title)
    for key, eng in _table():
        if key == n:
            return eng
    return title


def find_in_text(text: str, limit: int = 3) -> list[str]:
    """문장 속에 들어 있는 한국어 게임 이름을 찾아 영어 제목으로 돌려준다 (겹치지 않게, 최대 limit개)."""
    rest, out = _norm(text), []
    for key, eng in _table():
        if len(key) >= MIN_KEY_LEN and key in rest:
            if eng not in out:
                out.append(eng)
            rest = rest.replace(key, "|")
        if len(out) >= limit:
            break
    return out
