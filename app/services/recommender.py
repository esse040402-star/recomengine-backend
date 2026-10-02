"""장르/태그 기반 규칙형 추천 (algorithm_version = axis-tag-v1).

게임마다 '조작·전략·탐색·감성·휴식·경쟁' 6축 벡터를 장르/태그 사전으로 추정하고,
사용자의 6축과의 거리로 match_score(0~100)를 계산한다. 어디까지나 휴리스틱이므로
SIGNALS 사전을 고치면서 튜닝하면 된다.
"""
ALGORITHM_VERSION = "axis-tag-v1"

AXES = ["physical", "strategy", "exploration", "emotion", "comfort", "competition"]
AXIS_LABELS = {
    "physical": "조작·피지컬",
    "strategy": "전략·문제 해결",
    "exploration": "탐색·수집",
    "emotion": "감성·몰입",
    "comfort": "휴식·힐링",
    "competition": "경쟁·성취",
}


def _v(**kw: int) -> dict[str, int]:
    return kw


SIGNALS: dict[str, dict[str, int]] = {
    # --- 장르 (RAWG / IGDB 공통) ---
    "action": _v(physical=75, competition=55),
    "shooter": _v(physical=85, competition=75),
    "fighting": _v(physical=90, competition=85),
    "racing": _v(physical=75, competition=70),
    "sports": _v(physical=65, competition=80),
    "sport": _v(physical=65, competition=80),
    "platformer": _v(physical=80, comfort=50),
    "platform": _v(physical=80, comfort=50),
    "arcade": _v(physical=70, competition=60),
    "strategy": _v(strategy=90, competition=55),
    "turn-based strategy (tbs)": _v(strategy=92, physical=15),
    "real time strategy (rts)": _v(strategy=85, physical=60, competition=65),
    "tactical": _v(strategy=85),
    "puzzle": _v(strategy=85, comfort=70),
    "board games": _v(strategy=70, comfort=70),
    "card & board game": _v(strategy=70, comfort=70),
    "simulation": _v(strategy=65, comfort=75, exploration=55),
    "simulator": _v(strategy=65, comfort=75, exploration=55),
    "rpg": _v(emotion=75, exploration=70, strategy=60),
    "role-playing (rpg)": _v(emotion=75, exploration=70, strategy=60),
    "adventure": _v(exploration=80, emotion=75),
    "casual": _v(comfort=90, physical=25),
    "family": _v(comfort=85, competition=25),
    "educational": _v(strategy=65, comfort=75),
    "indie": _v(emotion=65),
    "massively multiplayer": _v(competition=60, exploration=60),
    "massively multiplayer online (mmo)": _v(competition=60, exploration=60),
    "moba": _v(competition=90, strategy=70, physical=70),
    "hack and slash/beat 'em up": _v(physical=85, competition=45),
    "visual novel": _v(emotion=90, physical=5),
    # --- 태그 / 테마 / 모드 ---
    "open world": _v(exploration=95),
    "exploration": _v(exploration=90),
    "sandbox": _v(exploration=80, comfort=65),
    "survival": _v(exploration=70, physical=60),
    "crafting": _v(exploration=70, comfort=70),
    "building": _v(strategy=70, comfort=75),
    "farming sim": _v(comfort=90, exploration=60),
    "metroidvania": _v(exploration=90, physical=75),
    "story rich": _v(emotion=90),
    "narrative": _v(emotion=85),
    "atmospheric": _v(emotion=80),
    "relaxing": _v(comfort=95, competition=15),
    "cozy": _v(comfort=95, competition=10),
    "souls-like": _v(physical=95, competition=55),
    "soulslike": _v(physical=95, competition=55),
    "difficult": _v(physical=85),
    "roguelike": _v(physical=65, strategy=70),
    "roguelite": _v(physical=65, strategy=70),
    "turn-based": _v(strategy=90, physical=15),
    "fps": _v(physical=85, competition=75),
    "pvp": _v(competition=95, physical=70),
    "competitive": _v(competition=95),
    "e-sports": _v(competition=95, physical=80),
    "co-op": _v(competition=35, comfort=65),
    "online co-op": _v(competition=35, comfort=65),
    "co-operative": _v(competition=35, comfort=65),
    "singleplayer": _v(comfort=60, competition=20),
    "single player": _v(comfort=60, competition=20),
    "multiplayer": _v(competition=60),
    "battle royale": _v(competition=90, physical=75),
    "horror": _v(emotion=70, comfort=15),
}

# 저사양 PC를 쓴다는 답(prefs.lowSpec)에 가산점을 줄 가벼운 게임 신호 (DB에 저사양 여부 컬럼이 없어서 쓰는 휴리스틱)
LOW_SPEC_TOKENS = {"2d", "pixel graphics", "pixel art", "retro", "indie", "casual"}
LOW_SPEC_BONUS = 8.0

# 사용자가 '피하고 싶다'고 한 요소 → 제외할 태그
AVOID_TAGS: dict[str, set[str]] = {
    "horror": {"horror", "gore", "psychological horror"},
    "pvp": {"pvp", "e-sports", "competitive", "battle royale", "moba"},
    "difficulty": {"difficult", "souls-like", "soulslike"},
    "mature": {"mature", "nudity", "sexual content", "gore"},
    # 과금/BM 피로: 태그로는 정확히 알 수 없어 '무료+과금 구조'를 암시하는 태그만 제외하는 보수적 휴리스틱
    "monetization": {"free to play", "microtransactions", "gacha", "in-app purchases"},
}

PLATFORM_KEYS: dict[str, tuple[str, ...]] = {
    "pc": ("pc", "macos", "linux"),
    "umpc": ("pc",),
    "console": ("playstation", "xbox", "nintendo"),
    "mobile": ("ios", "android"),
}


def game_vector(game: dict) -> tuple[list[float], list[str]]:
    tokens = {t.lower(): t for t in (game.get("genres") or []) + (game.get("tags") or [])}
    matched = [orig for low, orig in tokens.items() if low in SIGNALS]
    vec: list[float] = []
    for axis in AXES:
        vals = [SIGNALS[m.lower()][axis] for m in matched if axis in SIGNALS[m.lower()]]
        vec.append(sum(vals) / len(vals) if vals else 50.0)
    return vec, matched


def match_score(user: list[float], game: list[float]) -> float:
    weights = [1 + abs(u - 50) / 50 for u in user]  # 사용자가 강하게 반응한 축을 더 중요하게
    diff = sum(w * abs(u - g) for w, u, g in zip(weights, user, game)) / sum(weights)
    return round(max(0.0, min(100.0, 100 - diff)), 1)


def _platform_ok(game_platforms: list[str], wanted: list[str]) -> bool:
    if not wanted or not game_platforms:
        return True
    low = [p.lower() for p in game_platforms]
    return any(k in p for w in wanted for k in PLATFORM_KEYS.get(w, ()) for p in low)


def _avoided(game: dict, avoid: list[str]) -> bool:
    tokens = {t.lower() for t in (game.get("genres") or []) + (game.get("tags") or [])}
    return any(tokens & AVOID_TAGS.get(a, set()) for a in avoid)


def recommend(user_axes: list[float], games: list[dict], prefs: dict, limit: int = 10) -> list[dict]:
    wanted_platforms = [p for p in prefs.get("platforms", []) if isinstance(p, str)]
    avoid = [a for a in prefs.get("avoid", []) if isinstance(a, str)]
    top_axes = sorted(range(6), key=lambda i: user_axes[i], reverse=True)[:2]

    scored = []
    for g in games:
        if not _platform_ok(g.get("platforms") or [], wanted_platforms) or _avoided(g, avoid):
            continue
        vec, matched = game_vector(g)
        if not matched:
            continue
        # 사용자의 상위 2축과 관련된 태그를 우선 근거로 사용
        key_tags = [m for m in matched if any(AXES[i] in SIGNALS[m.lower()] for i in top_axes)]
        tags = (key_tags or matched)[:4]
        score = match_score(user_axes, vec)
        if prefs.get("lowSpec") and {t.lower() for t in (g.get("genres") or []) + (g.get("tags") or [])} & LOW_SPEC_TOKENS:
            score = min(100.0, round(score + LOW_SPEC_BONUS, 1))
        scored.append((score, g, tags))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for rank, (score, g, tags) in enumerate(scored[:limit], start=1):
        axis_names = " · ".join(AXIS_LABELS[AXES[i]] for i in top_axes)
        out.append(
            {
                "game_id": g["id"],
                "rank": rank,
                "match_score": score,
                "matched_tags": tags,
                "reason": f"{axis_names} 성향과 {', '.join(tags[:3])} 요소가 잘 맞아요.",
                "algorithm_version": ALGORITHM_VERSION,
            }
        )
    return out
