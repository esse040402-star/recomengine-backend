"""React 프론트의 게임 카탈로그에서 '프론트 게임 id -> 스팀 앱 번호' 표를 뽑아 data/catalog_apps.json 으로 저장한다.
프론트는 게임을 자기 id(elden, portal …)로 부르는데, 스팀에 물어보려면 앱 번호가 필요하고 그 대응표는 프론트 데이터에만 있다.

읽는 파일 (frontend/src/data/generated/):
  - catalog.json         게임 목록 (id, app, title)
  - marketSnapshot.json  저장된 뉴스 (전체 뉴스에서 조회할 '대표 게임'을 고르는 데 사용)

프론트의 게임 목록이 바뀌면 다시 실행하세요 (backend 폴더에서):
  python -m scripts.export_catalog
다른 위치의 프론트 데이터 폴더를 쓰려면:
  python -m scripts.export_catalog "C:\\경로\\frontend\\src\\data\\generated"
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "frontend" / "src" / "data" / "generated"
DEST = ROOT / "data" / "catalog_apps.json"
NEWS_GAME_COUNT = 12  # 게임 지정 없는 '전체 뉴스' 에서 조회할 대표 게임 수


def _load(folder: Path, name: str):
    path = folder / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        sys.exit(f"{path} 을(를) 읽을 수 없습니다. 프론트 폴더가 맞는지 확인하세요.")
    except ValueError:
        sys.exit(f"{path} 이(가) 올바른 JSON 이 아닙니다.")


def main(folder: str | None = None) -> None:
    source = Path(folder) if folder else DEFAULT_SOURCE
    catalog = _load(source, "catalog.json")
    if not isinstance(catalog, list) or not catalog:
        sys.exit("게임 카탈로그(catalog.json)가 비어 있거나 목록 형식이 아닙니다.")

    games = {}
    for g in catalog:
        if isinstance(g, dict) and g.get("id") and isinstance(g.get("app"), int):
            games[g["id"]] = {"app": g["app"], "title": g.get("title") or g["id"]}
    if not games:
        sys.exit("스팀 앱 번호(app)가 있는 게임이 없습니다.")

    # 프로토타입의 저장된 뉴스에 등장한 게임을 대표 게임으로 쓴다 (없으면 카탈로그 앞쪽 게임)
    snapshot = _load(source, "marketSnapshot.json")
    seen = []
    for n in (snapshot.get("news", []) if isinstance(snapshot, dict) else []):
        if isinstance(n, dict) and n.get("game") in games and n["game"] not in seen:
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
    if len(sys.argv) > 2:
        sys.exit("사용법: python -m scripts.export_catalog [프론트 데이터 폴더(frontend/src/data/generated)]")
    main(sys.argv[1] if len(sys.argv) == 2 else None)
