"""스팀 공개 엔드포인트 래퍼 (리뷰 / 가격 / 보유 게임). 네트워크가 필요해 직접 실행해 확인해야 한다."""
import re
from datetime import datetime, timezone

import httpx

from app.config import get_settings

STORE = "https://store.steampowered.com"


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
