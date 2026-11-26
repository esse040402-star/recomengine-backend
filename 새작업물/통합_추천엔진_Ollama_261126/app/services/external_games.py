import asyncio
import httpx

BASE_URL = "https://recomengine-game-api.onrender.com"



def _collect_named_values(value, target_keys: set[str]) -> list[str]:
    """외부 API의 Steam/IGDB 중첩 응답에서 장르·태그 이름을 안전하게 수집한다."""
    found: list[str] = []
    def add(item):
        if isinstance(item, str) and item.strip():
            found.append(item.strip())
        elif isinstance(item, dict):
            for key in ("name", "description", "tag", "value"):
                val = item.get(key)
                if isinstance(val, str) and val.strip():
                    found.append(val.strip())
                    break
    def walk(node):
        if isinstance(node, dict):
            for key, child in node.items():
                if str(key).lower() in target_keys:
                    if isinstance(child, list):
                        for item in child: add(item)
                    else:
                        add(child)
                walk(child)
        elif isinstance(node, list):
            for child in node: walk(child)
    walk(value)
    return list(dict.fromkeys(found))


def _platform_names(value) -> list[str]:
    names = []
    for item in value or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return list(dict.fromkeys(name for name in names if name.strip()))

def supports_pc_or_console(data: dict) -> bool:
    """PC 또는 콘솔 버전이 있는 게임만 허용한다."""
    steam = data.get("steam") or {}
    platforms = steam.get("platforms") or {}

    if any(platforms.get(key) is True for key in ("windows", "mac", "linux")):
        return True

    igdb = data.get("igdb") or {}
    game = igdb.get("game") or {}
    names = [
        str(item.get("name", "")).lower()
        for item in game.get("platforms") or []
        if isinstance(item, dict)
    ]

    keywords = (
        "pc (",
        "windows",
        "mac",
        "linux",
        "playstation",
        "xbox",
        "nintendo",
        "steam deck",
    )
    return any(any(keyword in name for keyword in keywords) for name in names)


async def search_external_games(query: str, page: int = 1, size: int = 20) -> dict:
    params = {"q": query, "page": page, "size": size}

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.get(f"{BASE_URL}/api/games", params=params)
        response.raise_for_status()
        result = response.json()

        items = result.get("items", [])
        details = await asyncio.gather(
            *(get_external_game(item["appid"], client=client) for item in items),
            return_exceptions=True,
        )

    filtered = []
    for item, detail in zip(items, details):
        if isinstance(detail, Exception) or not detail:
            continue
        if supports_pc_or_console(detail):
            steam = detail.get("steam") or {}
            igdb_game = (detail.get("igdb") or {}).get("game") or {}
            platform_names = _platform_names(igdb_game.get("platforms") or [])
            if not platform_names:
                platform_names = [name for key, name in (("windows", "PC"), ("mac", "Mac"), ("linux", "Linux"))
                                  if (steam.get("platforms") or {}).get(key) is True]
            genres = _collect_named_values(detail, {"genres", "genre"})
            tags = _collect_named_values(detail, {"tags", "categories", "game_modes", "themes", "keywords", "features"})
            release = steam.get("release_date") or igdb_game.get("first_release_date")
            if isinstance(release, dict):
                release = release.get("date")
            if isinstance(release, (int, float)):
                from datetime import datetime, timezone
                release = datetime.fromtimestamp(release, tz=timezone.utc).date().isoformat()
            price = steam.get("price_overview") or steam.get("price_info") or {}
            filtered.append({
                "id": f"steam-{item['appid']}",
                "appid": item["appid"],
                "steam_app_id": item["appid"],
                "title": steam.get("name") or item.get("name"),
                "name": item.get("name"),
                "header": steam.get("header_image"),
                "cover_url": steam.get("header_image"),
                "platforms": platform_names,
                "genres": genres,
                "tags": tags,
                "description": steam.get("short_description") or steam.get("about_the_game"),
                "release_date": release if isinstance(release, str) else None,
                "price_info": price if isinstance(price, dict) else {},
                "source": "external",
            })

    result["items"] = filtered
    return result


async def get_external_game(appid: int, client=None) -> dict | None:
    if client is not None:
        response = await client.get(f"{BASE_URL}/api/games/{appid}")
        response.raise_for_status()
        return response.json()

    async with httpx.AsyncClient(timeout=45) as own_client:
        response = await own_client.get(f"{BASE_URL}/api/games/{appid}")
        response.raise_for_status()
        return response.json()
