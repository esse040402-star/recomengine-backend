# 게임정보 수집 (Steam·IGDB → CSV/JSON)

추천 DB에 넣을 게임 정보를 Steam과 IGDB에서 모아 파일로 정리한 작업물입니다. `기존프로젝트` 코드는 바꾸지 않았고, 이 폴더만으로 실행됩니다.

## 수집 결과 (2026-11-20)

| 항목 | 값 |
|---|---|
| 게임 수 | **1,284개** (실패 0개) |
| IGDB 연결 | 1,276개 (Steam AppID 링크가 IGDB에 없는 8개는 `igdb_` 칸이 빈 값) |
| 수집 대상 | 프론트 카탈로그 137개 + IGDB 장르 20개별 Steam 리뷰 많은 순 100위 (Music 장르는 63개) |
| 결과 파일 | `data/collected/games.csv` (엑셀용, 40칸), `games.json` (같은 내용), `collect_report.json` (실패·빈 값 보고서) |

- 칸 이름 앞부분이 출처입니다: `steam_…` 은 Steam, `igdb_…` 는 IGDB 값.
- 장르·태그 이름은 통일하지 않고 원래 표현 그대로입니다. 통일은 `새작업물/API가중치_분류통합` 공통 사전이 맡습니다.
- 항목별 출처와 통합 기준: [`docs/게임정보_데이터출처_통합기준.md`](docs/게임정보_데이터출처_통합기준.md)
- 프론트 카탈로그에 있던 2026년 9월 신작 몇 개는 리뷰가 거의 없습니다. 추천에 쓸 때는 리뷰 수로 거르는 것을 권장합니다.
- Visual Novel 장르에는 성인 게임이 섞여 있을 수 있습니다 (Steam 장르의 Nudity·Sexual Content, IGDB 테마의 Erotic 확인).

## 파일

| 파일 | 내용 |
|---|---|
| `scripts/collect_game_info.py` | 수집 실행 파일 (외부 패키지 없이 파이썬 기본 기능만 사용) |
| `app/services/game_info_merge.py` | Steam·IGDB 원본을 출처별 칸으로 정리 (모바일 플랫폼 제외, Steam AppID로만 IGDB 연결) |
| `tests/test_game_info_merge.py` | 테스트 16개 (인터넷·키 불필요) |
| `data/catalog_apps.json` | 프론트 카탈로그 게임 목록 (`기존프로젝트/data/catalog_apps.json` 과 같은 내용) |

## 다시 수집하기 (Windows cmd, 이 폴더에서)

API 키는 이 폴더의 `.env` 에 `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET` 두 줄로 넣거나 환경변수로 지정합니다. `.env` 는 깃에 올리지 마세요.

```
python -m tests.test_game_info_merge
python -m scripts.collect_game_info --limit 3
python -m scripts.collect_game_info --top-per-genre 100 --pool-pages 10 --genres "Adventure,Role-playing (RPG),Shooter,Strategy,Simulator,Indie,Platform,Puzzle,Racing,Sport,Fighting,Hack and slash/Beat 'em up,Real Time Strategy (RTS),Turn-based strategy (TBS),Tactical,Card & Board Game,Visual Novel,Arcade,Point-and-click,Music"
```

- 첫 줄 테스트에서 `16 passed` 가 나오면 정상입니다.
- 세 번째 줄이 위 1,284개를 만든 명령입니다. 처음부터 받으면 약 2시간 걸립니다 (Steam 요청 사이 1.6초 대기).
- 받은 원본은 `data/collected/.cache/` 에 저장되어, 중간에 끊겨도 다시 실행하면 이어서 받습니다. 이 폴더는 깃에 올리지 않습니다.
- 다른 옵션: `--apps 620,730` (앱 번호 지정), `--top 1000` (리뷰 많은 순), `--no-catalog`, `--no-korean`, `--refresh`, `--no-igdb`
- 결과 파일은 실행할 때마다 그 실행의 대상만으로 새로 씁니다. 게임을 늘릴 때는 기존 장르를 포함해서 한 번에 실행하세요.

## 알려진 한계

- SteamSpy 장르별 목록(`request=genre`)은 2026-11-17 확인 시 빈 값만 돌려줘서, 전체 인기 목록을 후보로 받고 장르는 IGDB에서 확인합니다.
- SteamSpy 인기 목록 6·7페이지는 오류 페이지를 돌려줘서 건너뛰었습니다 (후보 약 6,400개).
- 리뷰 수와 설명은 수집 시점 기준입니다.
