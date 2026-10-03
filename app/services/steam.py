"""스팀 공개 엔드포인트 래퍼 (리뷰 / 가격 / 보유 게임 / 랭킹·뉴스·상세). 네트워크가 필요해 직접 실행해 확인해야 한다."""
import html
import json
import re
from datetime import datetime, timezone

import httpx

from app.config import get_settings

STORE = "https://store.steampowered.com"
API = "https://api.steampowered.com"
REVIEW_TEXT_MAX = 600  # 리뷰 카드에 보여줄 최대 글자 수 (넘으면 truncated=True)


async def fetch_reviews(app_id: int, num: int = 30, language: str = "all") -> list[dict]:
    """공개 리뷰 API (키 불필요). [{'text': str, 'voted_up': bool}]"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{STORE}/appreviews/{app_id}",
            params={"json": 1, "filter": "all", "language": language, "num_per_page": num, "purchase_type": "all"},
        )
        r.raise_for_status()
        data = r.json()
    return [
        {"text": x.get("review", ""), "voted_up": bool(x.get("voted_up"))}
        for x in data.get("reviews", [])
        if x.get("review")
    ]


async def fetch_prices(app_ids: list[int], cc: str = "kr") -> dict[int, dict]:
    """appdetails(price_overview) -> {app_id: price_info}. 무료/미판매 게임은 결과에서 빠진다."""
    out: dict[int, dict] = {}
    async with httpx.AsyncClient(timeout=20) as client:
        for i in range(0, len(app_ids), 20):
            batch = app_ids[i : i + 20]
            r = await client.get(
                f"{STORE}/api/appdetails",
                params={"appids": ",".join(map(str, batch)), "filters": "price_overview", "cc": cc},
            )
            if r.status_code != 200:
                continue
            for key, val in r.json().items():
                po = (val or {}).get("data")
                if val.get("success") and isinstance(po, dict) and po.get("price_overview"):
                    p = po["price_overview"]
                    out[int(key)] = {
                        "store": "steam",
                        "currency": p.get("currency"),
                        "initial": p.get("initial"),  # 최소 화폐 단위(센트 등) 원본값
                        "final": p.get("final"),
                        "discount_percent": p.get("discount_percent", 0),
                        "initial_formatted": p.get("initial_formatted") or None,
                        "final_formatted": p.get("final_formatted"),
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                    }
    return out


async def fetch_owned_games(steam_id: str) -> list[dict]:
    """GetOwnedGames (STEAM_API_KEY 필요, 프로필의 게임 목록이 공개여야 함). [{'name', 'playtime_minutes'}]"""
    if not re.fullmatch(r"\d{17}", steam_id):
        raise ValueError("steam_id는 17자리 숫자(SteamID64)여야 합니다.")
    key = get_settings().steam_api_key
    if not key:
        raise RuntimeError("STEAM_API_KEY가 설정되어 있지 않습니다.")
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
            params={"key": key, "steamid": steam_id, "include_appinfo": "true", "format": "json"},
        )
        r.raise_for_status()
        games = r.json().get("response", {}).get("games", [])
    return [{"name": g["name"], "playtime_minutes": g.get("playtime_forever", 0)} for g in games if g.get("name")]


# ---------------------------------------------------------------- 랭킹·뉴스·상세 (키 불필요한 공개 주소)
async def _get_json(url: str, params: dict, timeout: float = 15) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def fetch_most_played(limit: int = 10) -> list[dict]:
    """동시 접속 인기 차트 상위. [{'rank': 1, 'app': 730}]"""
    data = await _get_json(f"{API}/ISteamChartsService/GetMostPlayedGames/v1/", {})
    ranks = (data.get("response") or {}).get("ranks") or []
    return [{"rank": int(x["rank"]), "app": int(x["appid"])} for x in ranks[:limit] if x.get("appid")]


async def fetch_current_players(app_id: int) -> int | None:
    """지금 접속 중인 사람 수. 실패하면 None (차트 한 줄 때문에 전체가 실패하지 않게)."""
    try:
        data = await _get_json(f"{API}/ISteamUserStats/GetNumberOfCurrentPlayers/v1/", {"appid": app_id}, timeout=10)
    except httpx.HTTPError:
        return None
    count = (data.get("response") or {}).get("player_count")
    return int(count) if isinstance(count, int) else None


async def fetch_store_names(app_ids: list[int]) -> dict[int, str]:
    """앱 번호 -> 게임 이름(한국어 제공분은 한국어)."""
    if not app_ids:
        return {}
    payload = {
        "ids": [{"appid": a} for a in app_ids],
        "context": {"language": "koreana", "country_code": "KR"},
        "data_request": {},
    }
    data = await _get_json(f"{API}/IStoreBrowseService/GetItems/v1/", {"input_json": json.dumps(payload)})
    items = (data.get("response") or {}).get("store_items") or []
    return {int(x["appid"]): x["name"] for x in items if x.get("appid") and x.get("name")}


async def fetch_featured(cc: str = "kr") -> dict:
    """상점 메인 묶음(특가 specials / 신작 new_releases ...). 가격은 최소 화폐 단위(원 × 100)."""
    return await _get_json(f"{STORE}/api/featuredcategories", {"cc": cc, "l": "koreana"})


async def fetch_news(app_id: int, count: int = 3) -> list[dict]:
    """게임 공식 소식. [{'id', 'title', 'url', 'date', 'source'}]"""
    data = await _get_json(
        f"{API}/ISteamNews/GetNewsForApp/v2/", {"appid": app_id, "count": count, "maxlength": 1}
    )
    items = (data.get("appnews") or {}).get("newsitems") or []
    return [
        {"id": str(x.get("gid")), "title": x.get("title") or "", "url": x.get("url") or "",
         "date": int(x.get("date") or 0), "source": x.get("feedlabel") or ""}
        for x in items
        if x.get("title") and x.get("url")
    ]


async def fetch_review_summary(app_id: int) -> dict:
    """전체 언어 리뷰 집계. {'positive', 'negative', 'total', 'description'}"""
    data = await _get_json(
        f"{STORE}/appreviews/{app_id}",
        {"json": 1, "num_per_page": 0, "language": "all", "purchase_type": "all"},
    )
    q = data.get("query_summary") or {}
    return {
        "positive": int(q.get("total_positive") or 0),
        "negative": int(q.get("total_negative") or 0),
        "total": int(q.get("total_reviews") or 0),
        "description": q.get("review_score_desc") or "",
    }


async def fetch_review_page(app_id: int, sentiment: str = "all", language: str = "all", sort: str = "recent",
                            days: str = "all", cursor: str = "*", num: int = 12) -> dict:
    """리뷰 한 페이지. {'items': [...], 'cursor': 다음 페이지 표식 또는 None}
    스팀의 기간(day_range) 조건은 '도움순'에서만 먹기 때문에, 최신순의 기간 필터는 여기서 직접 거른다."""
    params = {
        "json": 1, "filter": "recent" if sort == "recent" else "all", "language": language,
        "review_type": sentiment, "purchase_type": "all", "num_per_page": num, "cursor": cursor or "*",
    }
    if days != "all" and sort != "recent":
        params["day_range"] = int(days)
    data = await _get_json(f"{STORE}/appreviews/{app_id}", params, timeout=20)
    min_created = datetime.now(timezone.utc).timestamp() - int(days) * 86400 if days != "all" and sort == "recent" else 0
    items = []
    for x in data.get("reviews") or []:
        text = (x.get("review") or "").strip()
        created = int(x.get("timestamp_created") or 0)
        if not text or created < min_created:
            continue
        author = x.get("author") or {}
        items.append({
            "id": str(x.get("recommendationid")),
            "text": text[:REVIEW_TEXT_MAX],
            "truncated": len(text) > REVIEW_TEXT_MAX,
            "positive": bool(x.get("voted_up")),
            "created": created,
            "updated": int(x.get("timestamp_updated") or created),
            "language": x.get("language") or "",
            "hours": round((author.get("playtime_forever") or 0) / 60, 1),
            "helpful": int(x.get("votes_up") or 0),
            "purchased": bool(x.get("steam_purchase")),
            "receivedFree": bool(x.get("received_for_free")),
            "url": f"https://steamcommunity.com/profiles/{author['steamid']}/recommended/{app_id}/" if author.get("steamid") else "",
        })
    next_cursor = data.get("cursor") if data.get("reviews") else None
    return {"items": items, "cursor": next_cursor}


def parse_requirements(raw: str | None) -> list[list[str]]:
    """스팀 사양 HTML(<ul><li><strong>운영 체제:</strong> Windows 10</li>…) -> [['운영 체제', 'Windows 10'], …].
    '항목:' 이름이 없는 줄은 '안내' 로 묶는다."""
    rows: list[list[str]] = []
    for li in re.findall(r"<li>(.*?)</li>", raw or "", flags=re.S):
        m = re.match(r"\s*<strong>(.*?)</strong>\s*(.*)", li, flags=re.S)
        if m:
            label, value = _plain(m.group(1)).rstrip(":： ").strip(), _plain(m.group(2))
        else:
            label, value = "안내", _plain(li)
        if value:
            rows.append([label or "안내", value])
    return rows


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


async def fetch_app_details(app_id: int, cc: str = "kr") -> dict | None:
    """게임 상세 -> 프론트 GAME_DETAILS 형식 일부. 스팀이 찾지 못하면 None."""
    data = await _get_json(f"{STORE}/api/appdetails", {"appids": app_id, "cc": cc, "l": "koreana"}, timeout=20)
    entry = data.get(str(app_id)) or {}
    d = entry.get("data")
    if not entry.get("success") or not isinstance(d, dict):
        return None
    languages = _plain(d.get("supported_languages") or "").replace(" *", "*")
    platforms = d.get("platforms") or {}
    pc = d.get("pc_requirements") if isinstance(d.get("pc_requirements"), dict) else {}
    details = {
        "developers": d.get("developers") or [],
        "publishers": d.get("publishers") or [],
        "releaseDate": (d.get("release_date") or {}).get("date") or "",
        "korean": "한국어" in languages,
        "languages": languages,
        "os": {k: bool(platforms.get(k)) for k in ("windows", "mac", "linux")},
        "minimum": parse_requirements(pc.get("minimum")),
        "recommended": parse_requirements(pc.get("recommended")),
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }
    po = d.get("price_overview")
    if isinstance(po, dict):
        details["price"] = {"price": po.get("final"), "originalPrice": po.get("initial"),
                            "discount": po.get("discount_percent", 0), "currency": po.get("currency")}
    elif d.get("is_free"):
        details["price"] = {"price": 0, "originalPrice": 0, "discount": 0, "currency": "KRW"}
    return details
