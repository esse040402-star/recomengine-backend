"""Steam + IGDB 원본 응답을 게임 1개 정보로 정리한다. 인터넷 요청은 하지 않는다 (순수 함수만).

이름 통일은 하지 않는다. 장르·태그·테마·플레이 방식은 Steam/IGDB 가 준 표현 그대로,
출처별 칸(steam_*, igdb_*)에 따로 저장한다. 표현 통일은 새작업물/API가중치_분류통합 의 공통 사전이 맡는다.
여기서 하는 일은 세 가지뿐이다.
  1) Steam AppID 로 연결된 IGDB 게임을 한 줄에 붙이기 (이름으로 연결하지 않음)
  2) 모바일 플랫폼 빼기
  3) HTML 제거, 날짜 형식(YYYY-MM-DD) 맞추기, 이미지 주소 만들기
"""
import html
import re
from datetime import datetime, timezone

IGDB_IMG = "https://images.igdb.com/igdb/image/upload/{size}/{image_id}.jpg"
DESCRIPTION_MAX = 3000  # 긴 소개문은 이 글자 수에서 자른다

# 모바일은 수집하지 않기로 함 (IGDB 플랫폼 이름, 소문자)
MOBILE_PLATFORMS = {
    "android", "ios", "windows phone", "windows mobile", "blackberry os", "palm os",
    "n-gage", "legacy mobile device", "symbian", "j2me",
}
STEAM_OS_KEYS = ("windows", "mac", "linux")
IGDB_MULTIPLAYER_FLAGS = ("campaigncoop", "onlinecoop", "offlinecoop", "lancoop", "splitscreen", "splitscreenonline", "dropin")


def _names(items, key: str = "name") -> list[str]:
    out, seen = [], set()
    for x in items or []:
        v = x.get(key) if isinstance(x, dict) else None
        if isinstance(v, str) and v.strip() and v.strip() not in seen:
            seen.add(v.strip())
            out.append(v.strip())
    return out


def _unique(items) -> list[str]:
    out = []
    for x in items or []:
        if isinstance(x, str) and x.strip() and x.strip() not in out:
            out.append(x.strip())
    return out


def plain_text(raw: str | None, limit: int = DESCRIPTION_MAX) -> str:
    """HTML 태그를 지우고 공백을 정리한다."""
    text = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", raw or "", flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text).strip()
    return text[:limit].rstrip() + ("…" if len(text) > limit else "")


def igdb_image(image_id: str | None, size: str) -> str | None:
    return IGDB_IMG.format(size=size, image_id=image_id) if image_id else None


def steam_release_date(text: str | None) -> str | None:
    """Steam(영어) 날짜 '24 Feb, 2022' / 'Feb 24, 2022' -> '2022-02-24'. 'Coming soon', 'Q1 2026' 은 None."""
    t = (text or "").strip().replace(".", "")
    for fmt in ("%d %b, %Y", "%b %d, %Y", "%d %B, %Y", "%B %d, %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def unix_to_date(ts) -> str | None:
    if not isinstance(ts, (int, float)):
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def igdb_companies(igdb: dict, role: str) -> list[str]:
    return _unique([
        ic["company"]["name"] for ic in igdb.get("involved_companies") or []
        if isinstance(ic, dict) and ic.get(role) and isinstance(ic.get("company"), dict) and ic["company"].get("name")
    ])


def igdb_multiplayer_flags(igdb: dict) -> list[str]:
    """IGDB multiplayer_modes 에서 true 인 항목 이름 (원래 필드 이름 그대로)."""
    flags = []
    for mm in igdb.get("multiplayer_modes") or []:
        if isinstance(mm, dict):
            flags += [f for f in IGDB_MULTIPLAYER_FLAGS if mm.get(f) is True]
    return _unique(flags)


def split_platforms(igdb: dict) -> tuple[list[str], list[str]]:
    """(모바일 뺀 IGDB 플랫폼, 뺀 모바일 플랫폼)."""
    keep, mobile = [], []
    for p in _names(igdb.get("platforms")):
        (mobile if p.lower() in MOBILE_PLATFORMS else keep).append(p)
    return keep, mobile


def _norm_title(name: str | None) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", (name or "").lower().replace("™", "").replace("®", ""))


def pick_igdb_match(candidates: list[dict], steam_name: str | None) -> dict | None:
    """같은 Steam AppID 에 IGDB 게임이 여러 개 연결된 경우(에디션 등)에만 쓴다.
    이름이 같은 것을, 없으면 id 가 가장 작은(먼저 등록된) 것을 고른다. 후보는 모두 Steam AppID 로 연결된 게임이다."""
    games = [g for g in candidates if isinstance(g, dict) and g.get("id")]
    if not games:
        return None
    target = _norm_title(steam_name)
    same = [g for g in games if target and _norm_title(g.get("name")) == target]
    return min(same or games, key=lambda g: g["id"])


def build_record(app_id: int, steam_en: dict | None, steam_ko: dict | None, reviews: dict | None,
                 igdb: dict | None, catalog_key: str | None = None) -> dict:
    """원본 응답들 -> 게임 정보 1개. 칸 이름 앞의 steam_/igdb_ 가 출처다.
    steam_en / steam_ko: Steam appdetails 의 data (l=english / l=koreana). 없으면 None
    reviews: Steam appreviews 의 query_summary. 없으면 None
    igdb: Steam AppID 로 연결된 IGDB games 응답 1개. 없으면 None
    """
    en, ko, rv, ig = steam_en or {}, steam_ko or {}, reviews or {}, igdb or {}
    igdb_platforms, mobile = split_platforms(ig)
    cover_id = ig["cover"].get("image_id") if isinstance(ig.get("cover"), dict) else None
    art_ids = [a.get("image_id") for a in ig.get("artworks") or [] if isinstance(a, dict) and a.get("image_id")]
    date_text = (en.get("release_date") or ko.get("release_date") or {}).get("date") or None
    coming_soon = (en.get("release_date") or {}).get("coming_soon")

    return {
        # 고유 ID
        "steam_app_id": app_id,
        "igdb_id": ig.get("id"),
        "catalog_key": catalog_key,
        # 이름
        "steam_name": en.get("name") or ko.get("name"),
        "steam_name_ko": ko.get("name") if ko.get("name") and ko.get("name") != en.get("name") else None,
        "igdb_name": ig.get("name"),
        # 이미지 URL
        "steam_header_image": en.get("header_image") or ko.get("header_image"),
        "steam_capsule_image": en.get("capsule_image") or ko.get("capsule_image"),
        "igdb_cover_image": igdb_image(cover_id, "t_cover_big"),
        "igdb_artwork_image": igdb_image(art_ids[0] if art_ids else None, "t_1080p"),
        # 설명 / 줄거리 (Steam 은 한국어 우선, 없으면 영어)
        # 한국어 소개가 이미지뿐이라 글자가 없으면 영어 소개를 쓴다
        "steam_short_description": plain_text(ko.get("short_description"), 600)
                                   or plain_text(en.get("short_description"), 600) or None,
        "steam_description": plain_text(ko.get("about_the_game")) or plain_text(en.get("about_the_game")) or None,
        "igdb_summary": plain_text(ig.get("summary")) or None,
        "igdb_storyline": plain_text(ig.get("storyline")) or None,
        # 장르 / 태그 / 테마 (원래 표현 그대로)
        "steam_genres": _names(en.get("genres"), "description"),
        "igdb_genres": _names(ig.get("genres")),
        "igdb_themes": _names(ig.get("themes")),
        "igdb_keywords": _names(ig.get("keywords")),
        "igdb_player_perspectives": _names(ig.get("player_perspectives")),
        # 플레이 방식 (원래 표현 그대로)
        "steam_categories": _names(en.get("categories"), "description"),
        "igdb_game_modes": _names(ig.get("game_modes")),
        "igdb_multiplayer_modes": igdb_multiplayer_flags(ig),
        # 지원 플랫폼 (모바일 제외)
        "steam_platforms": [k for k in STEAM_OS_KEYS if (en.get("platforms") or ko.get("platforms") or {}).get(k)],
        "igdb_platforms": igdb_platforms,
        "excluded_mobile_platforms": mobile,
        # 출시일
        "steam_release_date": steam_release_date(date_text),
        "steam_release_date_text": date_text,
        "steam_coming_soon": bool(coming_soon) if coming_soon is not None else None,
        "igdb_first_release_date": unix_to_date(ig.get("first_release_date")),
        # 개발사 / 배급사
        "steam_developers": _unique(en.get("developers") or ko.get("developers")),
        "steam_publishers": _unique(en.get("publishers") or ko.get("publishers")),
        "igdb_developers": igdb_companies(ig, "developer"),
        "igdb_publishers": igdb_companies(ig, "publisher"),
        # Steam 리뷰 수
        "steam_positive": rv.get("total_positive") if rv else None,
        "steam_negative": rv.get("total_negative") if rv else None,
        "steam_review_total": rv.get("total_reviews") if rv else None,
        # 무료 여부
        "steam_is_free": en["is_free"] if "is_free" in en else ko.get("is_free"),
        # 참고
        "steam_type": en.get("type") or ko.get("type"),
        "steam_url": f"https://store.steampowered.com/app/{app_id}/",
        "igdb_url": ig.get("url"),
    }


CSV_COLUMNS = [
    "steam_app_id", "igdb_id", "catalog_key", "steam_name", "steam_name_ko", "igdb_name",
    "steam_header_image", "steam_capsule_image", "igdb_cover_image", "igdb_artwork_image",
    "steam_short_description", "steam_description", "igdb_summary", "igdb_storyline",
    "steam_genres", "igdb_genres", "igdb_themes", "igdb_keywords", "igdb_player_perspectives",
    "steam_categories", "igdb_game_modes", "igdb_multiplayer_modes",
    "steam_platforms", "igdb_platforms", "excluded_mobile_platforms",
    "steam_release_date", "steam_release_date_text", "steam_coming_soon", "igdb_first_release_date",
    "steam_developers", "steam_publishers", "igdb_developers", "igdb_publishers",
    "steam_positive", "steam_negative", "steam_review_total", "steam_is_free",
    "steam_type", "steam_url", "igdb_url",
]
LIST_SEPARATOR = " | "


def to_csv_row(record: dict) -> dict:
    row = {}
    for col in CSV_COLUMNS:
        v = record.get(col)
        if isinstance(v, list):
            v = LIST_SEPARATOR.join(v)
        elif isinstance(v, bool):
            v = "TRUE" if v else "FALSE"
        elif v is None:
            v = ""
        row[col] = v
    return row
