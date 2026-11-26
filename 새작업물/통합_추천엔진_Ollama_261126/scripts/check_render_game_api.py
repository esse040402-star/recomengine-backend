"""Check the deployed RecomEngine Render game API from a machine with internet access.

Run: python -m scripts.check_render_game_api
"""
from __future__ import annotations

import asyncio
import httpx

from app.services.external_games import BASE_URL, supports_pc_or_console


async def main() -> None:
    timeout = httpx.Timeout(60.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for path, label in (("/", "Render home"), ("/docs", "Swagger docs"), ("/api/status", "API status")):
            response = await client.get(f"{BASE_URL}{path}")
            print(f"{label}: HTTP {response.status_code}")
            response.raise_for_status()

        search = await client.get(f"{BASE_URL}/api/games", params={"q": "elden", "page": 1, "size": 3})
        search.raise_for_status()
        payload = search.json()
        items = payload.get("items") or []
        print(f"Game search: {len(items)} result(s); total={payload.get('total', 'unknown')}")
        if not items:
            raise SystemExit("검색 API는 응답했지만 Elden 검색 결과가 없습니다.")

        first = items[0]
        appid = first.get("appid")
        if not appid:
            raise SystemExit(f"검색 결과에 appid가 없습니다: {first}")
        detail_response = await client.get(f"{BASE_URL}/api/games/{appid}")
        detail_response.raise_for_status()
        detail = detail_response.json()
        steam = detail.get("steam") or {}
        igdb_game = (detail.get("igdb") or {}).get("game") or {}
        platforms = [x.get("name") for x in (igdb_game.get("platforms") or []) if isinstance(x, dict)]
        print(f"Detail: appid={appid}, title={steam.get('name') or first.get('name')}")
        print(f"Steam platforms: {steam.get('platforms')}")
        print(f"IGDB platforms: {platforms}")
        print(f"PC/console eligible: {supports_pc_or_console(detail)}")
        print(f"Steam genres/categories: {len(steam.get('genres') or [])}/{len(steam.get('categories') or [])}")
        print(f"IGDB genres/themes/keywords: {len(igdb_game.get('genres') or [])}/{len(igdb_game.get('themes') or [])}/{len(igdb_game.get('keywords') or [])}")
        print("Render API connectivity check completed.")


if __name__ == "__main__":
    asyncio.run(main())
