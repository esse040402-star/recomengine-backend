"""RAWG/IGDB에서 가져온 게임 데이터를 DB에 넣기 전에 정리한다 (외부 패키지 없음).
- 장르 이름 통일: 두 서비스가 같은 장르를 다른 이름으로 부른다 (RAWG 'Platformer' = IGDB 'Platform')
- 취향과 무관한 태그 제거: 'Steam Achievements', 'Full controller support' 같은 스팀 기능 표시
- 사용자가 올린 비공식 항목 제외: 평가·추가 수가 거의 없는 RAWG 항목
목록을 고치고 싶으면 이 파일의 상수만 수정하면 된다."""
import re

# IGDB(또는 RAWG 변형) 장르 -> (통일한 장르, 덧붙일 태그)
GENRE_MAP: dict[str, tuple[str, list[str]]] = {
    "platform": ("Platformer", []),
    "role-playing (rpg)": ("RPG", []),
    "simulator": ("Simulation", []),
    "sport": ("Sports", []),
    "card & board game": ("Board Games", []),
    "card": ("Board Games", []),
    "real time strategy (rts)": ("Strategy", ["RTS"]),
    "turn-based strategy (tbs)": ("Strategy", ["Turn-Based"]),
    "tactical": ("Strategy", ["Tactical"]),
    "hack and slash/beat 'em up": ("Action", ["Hack and Slash"]),
    "point-and-click": ("Adventure", ["Point & Click"]),
    "quiz/trivia": ("Casual", ["Trivia"]),
    "pinball": ("Arcade", ["Pinball"]),
    "massively multiplayer online (mmo)": ("Massively Multiplayer", []),
}

# IGDB 테마/게임 모드/시점 이름 -> RAWG 태그 이름 (None 이면 버림)
TAG_MAP: dict[str, str | None] = {
    "single player": "Singleplayer",
    "co-operative": "Co-op",
    "split screen": "Split Screen",
    "massively multiplayer online (mmo)": "MMO",
    "science fiction": "Sci-fi",
    "first person": "First-Person",
    "third person": "Third Person",
    "bird view / isometric": "Isometric",
    "side view": "2D",
    "4x (explore, expand, exploit, and exterminate)": "4X",
    "erotic": "Sexual Content",  # 불호 필터(mature)가 알아보도록
    "non-fiction": None,
    "text": None,
    "auditory": None,
}

# 게임 성향이 아니라 플랫폼 기능 표시인 태그 (소문자)
TAG_STOPLIST = {
    "steam achievements", "full controller support", "partial controller support", "controller", "controller support",
    "steam cloud", "steam-trading-cards", "steam trading cards", "steam leaderboards", "steam workshop",
    "steam turn notifications", "steamvr collectibles", "steam timeline", "valve anti-cheat enabled",
    "remote play on tv", "remote play on phone", "remote play on tablet", "remote play together",
    "family sharing", "stats", "achievements", "cloud saves", "includes level editor", "includes source sdk",
    "commentary available", "captions available", "tracked controller support", "steam is learning about this game",
    "overlay", "hdr available", "mods", "mods (require hl2)", "exclusive", "true exclusive",
}
MAX_TAGS = 40

# 이 기준을 하나도 넘지 못하는 RAWG 항목은 사용자가 올린 비공식 항목으로 보고 건너뛴다
MIN_RATINGS = 5     # 평가 수
MIN_ADDED = 50      # 라이브러리에 추가한 사용자 수


def _dedupe_ci(items: list[str]) -> list[str]:
    seen, out = set(), []
    for x in items:
        k = x.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(x.strip())
    return out


def normalize(genres: list[str] | None, tags: list[str] | None) -> tuple[list[str], list[str]]:
    """(장르, 태그) 정리: 장르 이름 통일 -> 태그 이름 통일 -> 기능 태그 제거 -> 장르와 같은 태그 제거 -> 중복 제거."""
    out_genres, extra_tags = [], []
    for g in genres or []:
        mapped, extra = GENRE_MAP.get(g.strip().lower(), (g.strip(), []))
        out_genres.append(mapped)
        extra_tags += extra
    out_genres = _dedupe_ci(out_genres)
    genre_keys = {g.lower() for g in out_genres}

    out_tags = []
    for t in list(tags or []) + extra_tags:
        key = t.strip().lower()
        if key in TAG_MAP:
            if TAG_MAP[key] is None:
                continue
            t, key = TAG_MAP[key], TAG_MAP[key].lower()
        if not key or key in TAG_STOPLIST or key in genre_keys:
            continue
        out_tags.append(t)
    return out_genres, _dedupe_ci(out_tags)[:MAX_TAGS]


def clean_row(row: dict) -> dict:
    genres, tags = normalize(row.get("genres"), row.get("tags"))
    return {**row, "genres": genres, "tags": tags}


def is_minor_rawg_entry(hit: dict) -> bool:
    """RAWG 검색 결과 중 평가도, 추가한 사람도, 메타크리틱 점수도 거의 없는 항목 (팬 제작물·잘못 등록된 항목 등)."""
    return (
        (hit.get("ratings_count") or 0) < MIN_RATINGS
        and (hit.get("added") or 0) < MIN_ADDED
        and not hit.get("metacritic")
    )


STEAM_APP_RE = re.compile(r"store\.steampowered\.com/app/(\d+)")


def steam_app_id_from_url(url: str | None) -> int | None:
    m = STEAM_APP_RE.search(url or "")
    return int(m.group(1)) if m else None
