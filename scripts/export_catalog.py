"""프로토타입 HTML 의 게임 카탈로그에서 '프론트 게임 id -> 스팀 앱 번호' 표를 뽑아 data/catalog_apps.json 으로 저장한다.
프론트는 게임을 자기 id(elden, portal …)로 부르는데, 스팀에 물어보려면 앱 번호가 필요하고 그 대응표는 HTML 안에만 있다.
(약 32MB 인 HTML 자체는 저장소에 넣지 않고, 이 작은 표만 저장소에 둔다.)

프론트의 게임 목록이 바뀌면 다시 실행하세요 (backend 폴더에서):
  python -m scripts.export_catalog "C:\\경로\\화면 프로토타입.html"
"""
import json
import re
import sys
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "data" / "catalog_apps.json"
NEWS_GAME_COUNT = 12  # 게임 지정 없는 '전체 뉴스' 에서 조회할 대표 게임 수


def _json_after(text: str, pattern: str, opener: str):
    m = re.search(pattern, text)
    if not m:
        return None
    start = text.find(opener, m.end() - 1)
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError:
        return None
    return obj


def main(path: str) -> None:
    html = Path(path).read_text(encoding="utf-8")
    catalog = _json_after(html, r"\bCATALOG\s*=\s*\[", "[")
    if not isinstance(catalog, list) or not catalog:
        sys.exit("게임 카탈로그(CATALOG)를 찾지 못했습니다. 다른 파일이 아닌지 확인하세요.")

    games = {}
    for g in catalog:
        if isinstance(g, dict) and g.get("id") and isinstance(g.get("app"), int):
            games[g["id"]] = {"app": g["app"], "title": g.get("title") or g["id"]}
    if not games:
        sys.exit("스팀 앱 번호(app)가 있는 게임이 없습니다.")

    # 프로토타입의 저장된 뉴스에 등장한 게임을 대표 게임으로 쓴다 (없으면 카탈로그 앞쪽 게임)
    snapshot = _json_after(html, r"MARKET_SNAPSHOT\s*=\s*\{", "{") or {}
    seen = []
    for n in snapshot.get("news", []):
        if n.get("game") in games and n["game"] not in seen:
            seen.append(n["game"])
    for gid in games:
        if len(seen) >= NEWS_GAME_COUNT:
            break
        if gid not in seen:
            seen.append(gid)

    DEST.parent.mkdir(exist_ok=True)
    DEST.write_text(
        json.dumps({"news_games": seen[:NEWS_GAME_COUNT], "games": games}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"게임 {len(games)}개, 대표 뉴스 게임 {len(seen[:NEWS_GAME_COUNT])}개 저장 -> {DEST}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python -m scripts.export_catalog <프로토타입 html 경로>")
    main(sys.argv[1])
