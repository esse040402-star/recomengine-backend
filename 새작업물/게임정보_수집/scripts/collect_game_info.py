"""게임 필수 정보를 Steam + IGDB 에서 모아 JSON / CSV 로 저장한다.

실행 (backend 폴더 = 기존프로젝트 에서, 가상환경 켠 상태):
  python -m scripts.collect_game_info                    # data/catalog_apps.json 의 게임 전부
  python -m scripts.collect_game_info --apps 1245620,620 # 스팀 앱 번호를 직접 지정
  python -m scripts.collect_game_info --limit 5          # 앞의 5개만 (시험용)
  python -m scripts.collect_game_info --refresh          # 저장해 둔 원본(캐시)을 무시하고 새로 받기
  python -m scripts.collect_game_info --top 1000         # 카탈로그 + Steam 리뷰 수 상위 1000개 (SteamSpy 목록)
  python -m scripts.collect_game_info --top-per-genre 100   # 카탈로그 + 장르별(IGDB 장르) 상위 100개씩
  python -m scripts.collect_game_info --top 3000 --no-korean # 많이 받을 때: 한국어 요청을 빼서 더 빠르게

결과 (기본 폴더 data/collected/):
  games.json            게임 정보 전체 (칸 이름 앞의 steam_/igdb_ 가 출처)
  games.csv             같은 내용을 엑셀용 표로 (목록은 " | " 로 이어 붙임)
  collect_report.json   비어 있는 항목 개수, IGDB 연결 실패 게임 등
  .cache/               받아 온 원본 응답. 중간에 끊겨도 다시 실행하면 이어서 받는다 (깃에 올리지 마세요)

필요한 키 (.env): IGDB_CLIENT_ID, IGDB_CLIENT_SECRET  — 없으면 Steam 정보만 모은다.
키 값은 화면/파일 어디에도 출력하지 않는다.
외부 패키지 없이 파이썬 표준 라이브러리만 사용한다.
"""
import argparse
import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.services.game_info_merge import CSV_COLUMNS, build_record, pick_igdb_match, to_csv_row

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog_apps.json"
DEFAULT_OUT = ROOT / "data" / "collected"

STORE = "https://store.steampowered.com"
STEAM_API = "https://api.steampowered.com"
IGDB_API = "https://api.igdb.com/v4"
TWITCH_TOKEN = "https://id.twitch.tv/oauth2/token"

STEAM_DELAY = 1.6      # 초. 스팀 상점 API는 IP당 약 5분 200회 제한 -> 요청 사이에 쉰다
STEAM_BACKOFF = 65     # 429(요청 너무 많음)를 받으면 이만큼 쉬고 다시
IGDB_DELAY = 0.3       # IGDB 는 초당 4회 제한
IGDB_BATCH = 100       # IGDB 한 번에 묻는 게임 수
STEAM_SOURCE_ID = 1    # IGDB external_game_source / category 에서 Steam 번호
STEAM_URL_RE = re.compile(r"store\.steampowered\.com/app/(\d+)")
IGDB_FIELDS = (
    "id,name,url,summary,storyline,first_release_date,genres.name,themes.name,game_modes.name,"
    "player_perspectives.name,keywords.name,platforms.name,multiplayer_modes.*,cover.image_id,"
    "artworks.image_id,screenshots.image_id,involved_companies.company.name,"
    "involved_companies.developer,involved_companies.publisher"
)
USER_AGENT = "RecomEngine-school-project/1.0 (game info collector)"


# ------------------------------------------------------------------ 설정


def load_env(path: Path) -> dict:
    """.env 를 읽는다 (값은 절대 출력하지 않음). 백엔드와 같은 방식(python-dotenv)으로 읽고,
    키 이름의 대소문자는 구분하지 않는다. 이미 환경변수에 있으면 그게 우선."""
    raw: dict = {}
    try:
        from dotenv import dotenv_values  # requirements.txt 에 있음 (백엔드 설정도 이걸로 .env 를 읽음)
        raw = dict(dotenv_values(path, encoding="utf-8-sig"))
    except ImportError:
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if line.startswith("export "):
                    line = line[7:]
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip()
                if v[:1] in "\"'" and v[:1] and v.count(v[0]) >= 2:
                    v = v[1:v.index(v[0], 1)]
                else:
                    v = v.split(" #", 1)[0].strip()
                raw[k.strip()] = v
        except OSError:
            pass
    except OSError:
        pass
    values = {k.strip().upper(): (v or "").strip() for k, v in raw.items() if k}
    for k in ("IGDB_CLIENT_ID", "IGDB_CLIENT_SECRET"):
        if os.environ.get(k):
            values[k] = os.environ[k].strip()
    return values


def load_catalog() -> list[tuple[int, str | None]]:
    try:
        games = json.loads(CATALOG.read_text(encoding="utf-8"))["games"]
    except (OSError, ValueError, KeyError):
        sys.exit(f"{CATALOG} 를 읽을 수 없습니다. --apps 로 스팀 앱 번호를 직접 넣거나 "
                 "python -m scripts.export_catalog 를 먼저 실행하세요.")
    return [(g["app"], key) for key, g in games.items() if isinstance(g.get("app"), int)]


def load_targets(args, cache=None) -> list[tuple[int, str | None]]:
    """(스팀 앱 번호, 프론트 카탈로그 id) 목록.
    기본 = 프론트 카탈로그. --apps 를 주면 그 목록. --no-catalog 면 카탈로그를 빼고.
    --top / --top-per-genre 를 주면 SteamSpy 인기 게임을 뒤에 덧붙인다 (중복 제거)."""
    if args.apps:
        targets = [(int(x), None) for x in re.split(r"[,\s]+", args.apps) if x.strip().isdigit()]
    elif getattr(args, "no_catalog", False):
        targets = []
    else:
        targets = load_catalog()
    if getattr(args, "top", 0) or getattr(args, "top_per_genre", 0):
        targets += [(a, None) for a in popular_apps(args, cache)]
    seen, out = set(), []
    for app, key in targets:
        if app not in seen:
            seen.add(app)
            out.append((app, key))
    return out[: args.limit] if args.limit else out


# ------------------------------------------------------------------ 인기 게임 목록 (SteamSpy)

STEAMSPY = "https://steamspy.com/api.php"
STEAMSPY_DELAY = 61  # 초. SteamSpy 는 전체 목록(all) 요청을 1분에 1번 정도로 제한한다
STEAMSPY_PAGE_SIZE = 1000
# SteamSpy 의 장르/태그별 목록(request=genre, tag)은 2026-11-17 확인 시 빈 값 {} 만 돌려줘서 쓰지 않는다.
# 대신 전체 인기 목록(request=all) 몇 페이지를 후보로 받고, 장르는 IGDB 에서 확인해 장르별로 고른다.
# 장르 이름은 IGDB 표기 그대로 쓴다 (이름 통일 없음).
DEFAULT_GENRES = ["Adventure", "Role-playing (RPG)", "Shooter", "Strategy", "Simulator", "Indie",
                  "Platform", "Puzzle", "Racing", "Sport"]
GENRE_POOL_PAGES = 3  # 장르별 고르기에 쓰는 후보 = SteamSpy 인기 목록 3페이지 (약 3,000개)
_last_spy = [0.0]


def steamspy_list(params: dict, cache) -> dict:
    """SteamSpy 목록 요청 (결과는 캐시). {앱번호 문자열: {name, positive, negative, ...}}
    빈 결과는 고장/일시 오류로 보고 캐시에 남기지 않는다."""
    name = "steamspy_" + "_".join(f"{k}-{re.sub(r'[^0-9A-Za-z]+', '', str(v))}" for k, v in params.items())
    if cache is not None:
        cached = cache.get(name)
        if cached:
            return cached
    wait = STEAMSPY_DELAY - (time.time() - _last_spy[0])
    if _last_spy[0] and wait > 0:
        print(f"  SteamSpy 요청 제한 때문에 {int(wait)}초 기다립니다…")
        time.sleep(wait)
    _last_spy[0] = time.time()
    data = http_json(STEAMSPY, params, timeout=90)
    if not isinstance(data, dict) or not data:
        raise HttpError(-1, "SteamSpy 가 빈 목록을 돌려줌 (잠시 뒤 다시 시도)")
    if cache is not None:
        cache.put(name, data)
    return data


def steamspy_pool(pages: int, cache) -> dict:
    rows: dict = {}
    print(f"SteamSpy 에서 인기 게임 목록 {pages}페이지를 받습니다 (페이지당 약 1분, 받아둔 페이지는 건너뜀)…")
    failed_pages = []
    for page in range(pages):
        for attempt in range(2):  # SteamSpy 가 가끔 JSON 대신 오류 페이지를 줘서 한 번 더 시도
            try:
                rows.update(steamspy_list({"request": "all", "page": page}, cache))
                break
            except HttpError as e:
                if attempt == 0:
                    print(f"  {page + 1}페이지 실패 ({e}). 1분 뒤 한 번 더 시도합니다…")
                    continue
                print(f"  {page + 1}페이지는 건너뜁니다. 나중에 다시 실행하면 이 페이지만 다시 받습니다.")
                failed_pages.append(page + 1)
    if not rows:
        raise HttpError(-1, "SteamSpy 인기 목록을 한 페이지도 받지 못함")
    if failed_pages:
        print(f"  받지 못한 페이지: {failed_pages} (받은 페이지만으로 계속 진행)")
    return rows


def igdb_genres_for(apps: list[int], cache) -> dict[int, list[str]]:
    """앱 번호 -> IGDB 장르 이름 목록 (Steam AppID 로 연결된 IGDB 게임 기준, 100개씩 묶어서 조회)."""
    name = f"igdb_genres_pool_{len(apps)}_{apps[0] if apps else 0}"
    cached = cache.get(name) if cache is not None else None
    if cached:
        return {int(k): v for k, v in cached.items()}
    env = load_env(ROOT / ".env")
    if not (env.get("IGDB_CLIENT_ID") and env.get("IGDB_CLIENT_SECRET")):
        sys.exit("장르별 고르기에는 IGDB 키가 필요합니다 (.env 의 IGDB_CLIENT_ID / IGDB_CLIENT_SECRET).")
    ig = Igdb(env["IGDB_CLIENT_ID"], env["IGDB_CLIENT_SECRET"])
    ig.login()
    print(f"IGDB 에서 후보 {len(apps)}개의 장르를 확인합니다…")
    links = ig.steam_links(apps)
    gids = sorted({min(ids) for ids in links.values() if ids})
    genres_by_gid: dict[int, list[str]] = {}
    for i in range(0, len(gids), IGDB_BATCH):
        chunk = ",".join(str(x) for x in gids[i:i + IGDB_BATCH])
        for g in ig.query("games", f"fields genres.name; where id = ({chunk}); limit 500;"):
            genres_by_gid[g["id"]] = [x["name"] for x in g.get("genres") or [] if isinstance(x, dict) and x.get("name")]
    out = {app: genres_by_gid.get(min(ids), []) for app, ids in links.items() if ids}
    if cache is not None:
        cache.put(name, {str(k): v for k, v in out.items()})
    return out


def _ranked(rows: dict, min_reviews: int) -> list[int]:
    """리뷰 수(긍정+부정)가 많은 순서의 앱 번호."""
    items = []
    for k, v in rows.items():
        if not str(k).isdigit() or not isinstance(v, dict):
            continue
        total = int(v.get("positive") or 0) + int(v.get("negative") or 0)
        if total >= min_reviews:
            items.append((total, int(k)))
    return [app for _, app in sorted(items, reverse=True)]


def popular_apps(args, cache) -> list[int]:
    """SteamSpy 로 '리뷰 수가 많은 Steam 게임' 목록을 만든다. 실제 리뷰 수·정보는 나중에 Steam 에서 다시 받는다."""
    out: list[int] = []
    min_reviews = getattr(args, "min_reviews", 0) or 0
    if args.top:
        pages = min(50, -(-args.top // STEAMSPY_PAGE_SIZE))  # 올림
        ranked = _ranked(steamspy_pool(pages, cache), min_reviews)[: args.top]
        print(f"  인기 게임 {len(ranked)}개 (리뷰 수 많은 순)")
        out += ranked
    if args.top_per_genre:
        genres = [g.strip() for g in (args.genres or ",".join(DEFAULT_GENRES)).split(",") if g.strip()]
        pool = _ranked(steamspy_pool(max(GENRE_POOL_PAGES, getattr(args, "pool_pages", 0) or 0), cache), min_reviews)
        app_genres = igdb_genres_for(pool, cache)
        print(f"장르 {len(genres)}개에서 리뷰 많은 순으로 {args.top_per_genre}개씩 고릅니다 (장르 이름은 IGDB 기준)")
        for g in genres:
            picked = [a for a in pool if g.lower() in (x.lower() for x in app_genres.get(a, []))][: args.top_per_genre]
            print(f"  {g}: {len(picked)}개")
            out += picked
    return out


# ------------------------------------------------------------------ HTTP


class HttpError(Exception):
    def __init__(self, status: int, message: str = ""):
        super().__init__(f"HTTP {status} {message}".strip())
        self.status = status


def _ssl_context() -> ssl.SSLContext:
    """인증서 확인용 설정. 파이썬 기본 인증서 목록에 없는 인증서(백신의 HTTPS 검사, 윈도우가 나중에 받는 루트 인증서 등)
    때문에 CERTIFICATE_VERIFY_FAILED 가 나는 PC가 있어서, 윈도우 인증서 저장소(truststore) -> certifi -> 기본 순서로 쓴다.
    인증서 확인을 끄지는 않는다."""
    try:
        import truststore  # fastapi[standard] 설치 때 같이 설치됨
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        pass
    try:
        import certifi  # httpx 설치 때 같이 설치됨
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()


def http_json(url: str, params: dict | None = None, data: bytes | None = None, headers: dict | None = None,
              timeout: float = 20):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})},
                                 method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as r:
            body = r.read().decode("utf-8", "replace")
        try:
            return json.loads(body)
        except ValueError:
            # 주소가 바뀌어 JSON 대신 웹페이지(HTML)를 주는 경우 등
            raise HttpError(-1, "JSON 이 아닌 응답 (API 주소나 형식이 바뀌었을 수 있음)") from None
    except urllib.error.HTTPError as e:
        # 주소에 키가 들어갈 수 있으므로 주소는 메시지에 넣지 않는다. 서버가 돌려준 오류 문구(JSON)만 짧게 보여준다
        detail = ""
        try:
            body = json.loads(e.read().decode("utf-8", "replace"))
            if isinstance(body, dict):
                detail = str(body.get("message") or body.get("title") or body.get("cause") or "")[:150]
            elif isinstance(body, list) and body and isinstance(body[0], dict):
                detail = str(body[0].get("title") or body[0].get("cause") or "")[:150]
        except Exception:
            pass
        raise HttpError(e.code, detail) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise HttpError(0, f"연결 실패: {getattr(e, 'reason', e)}") from None


class Cache:
    def __init__(self, folder: Path, refresh: bool):
        self.folder, self.refresh = folder, refresh
        folder.mkdir(parents=True, exist_ok=True)

    def get(self, name: str):
        p = self.folder / f"{name}.json"
        if self.refresh or not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return None

    def put(self, name: str, value) -> None:
        (self.folder / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ Steam

_last_steam = [0.0]


def steam_get(url: str, params: dict):
    for attempt in range(4):
        wait = STEAM_DELAY - (time.time() - _last_steam[0])
        if wait > 0:
            time.sleep(wait)
        _last_steam[0] = time.time()
        try:
            return http_json(url, params)
        except HttpError as e:
            if e.status in (429, 403) and attempt < 3:
                print(f"    스팀이 잠시 요청을 막았습니다 ({e.status}). {STEAM_BACKOFF}초 쉬고 다시 시도합니다…")
                time.sleep(STEAM_BACKOFF)
                continue
            if e.status in (0, 500, 502, 503) and attempt < 3:
                time.sleep(5)
                continue
            raise
    return None


def steam_details(app_id: int, lang: str, cache: Cache) -> dict | None:
    """appdetails 의 data. 한국 상점에 없으면 미국 상점으로 다시 묻는다. 없으면 {} (캐시에 '없음' 기록)."""
    name = f"steam_{app_id}_{lang}"
    cached = cache.get(name)
    if cached is not None:
        return cached or None
    data = {}
    for cc in ("kr", "us"):
        resp = steam_get(f"{STORE}/api/appdetails", {"appids": app_id, "cc": cc, "l": lang}) or {}
        entry = resp.get(str(app_id)) or {}
        if entry.get("success") and isinstance(entry.get("data"), dict):
            data = entry["data"]
            break
    cache.put(name, data)
    return data or None


def steam_reviews(app_id: int, cache: Cache) -> dict | None:
    """리뷰 개수 요약 (본문은 1개만 받고 버림).
    예전 주소(store.steampowered.com/appreviews)는 이제 JSON 대신 HTML 을 줘서, 공식 리뷰 API
    IUserReviewsService/GetAppReviews 를 쓴다. 요청 값은 팀 백엔드(기존프로젝트/app/services/steam.py)의
    리뷰 집계와 같다: 모든 언어, 전체 기간, purchase_type=1."""
    name = f"steam_{app_id}_reviews2"
    cached = cache.get(name)
    if cached is not None:
        return cached or None
    payload = {"appid": app_id, "filter": 0, "day_range": 0, "languages": ["all"], "review_type": 0,
               "purchase_type": 1, "num_per_page": 1, "cursor": "*"}
    raw = steam_get(f"{STEAM_API}/IUserReviewsService/GetAppReviews/v1/",
                    {"input_json": json.dumps(payload)}) or {}
    data = raw.get("response") if isinstance(raw, dict) else None
    if not isinstance(data, dict):
        raise HttpError(-1, "Steam 리뷰 응답 형식이 올바르지 않음")
    q = data.get("query_summary") or {}
    summary = {k: q.get(k) for k in ("total_positive", "total_negative", "total_reviews", "review_score_desc")
               if q.get(k) is not None}
    cache.put(name, summary)
    return summary or None


# ------------------------------------------------------------------ IGDB


class Igdb:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id, self.client_secret = client_id, client_secret
        self.token = None
        self._last = 0.0

    def login(self) -> None:
        data = http_json(TWITCH_TOKEN, data=urllib.parse.urlencode({
            "client_id": self.client_id, "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }).encode())
        self.token = data["access_token"]

    def query(self, endpoint: str, body: str) -> list[dict]:
        for attempt in range(3):
            wait = IGDB_DELAY - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                return http_json(f"{IGDB_API}/{endpoint}", data=body.encode(), headers={
                    "Client-ID": self.client_id, "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                }) or []
            except HttpError as e:
                if e.status == 429 and attempt < 2:
                    time.sleep(2)
                    continue
                raise
        return []

    def steam_links(self, app_ids: list[int]) -> dict[int, list[int]]:
        """스팀 앱 번호 -> 연결된 IGDB 게임 id 목록."""
        out: dict[int, list[int]] = {}
        for i in range(0, len(app_ids), IGDB_BATCH):
            chunk = app_ids[i:i + IGDB_BATCH]
            uids = ",".join(f'"{a}"' for a in chunk)
            try:
                rows = self.query("external_games",
                                  f"fields game,uid,url,external_game_source; where uid = ({uids}); limit 500;")
            except HttpError as e:
                if e.status != 400:
                    raise
                # 예전 필드 이름(category)만 받는 경우 대비
                rows = self.query("external_games", f"fields game,uid,url,category; where uid = ({uids}); limit 500;")
            wanted = set(chunk)
            for r in rows:
                if not str(r.get("uid", "")).isdigit() or not r.get("game"):
                    continue
                app = int(r["uid"])
                url_match = STEAM_URL_RE.search(r.get("url") or "")
                is_steam = (r.get("external_game_source") == STEAM_SOURCE_ID or r.get("category") == STEAM_SOURCE_ID
                            or (url_match and int(url_match.group(1)) == app))
                if app in wanted and is_steam:
                    out.setdefault(app, []).append(r["game"])
        return out

    def games(self, ids: list[int]) -> dict[int, dict]:
        out = {}
        ids = sorted(set(ids))
        for i in range(0, len(ids), IGDB_BATCH):
            chunk = ",".join(str(x) for x in ids[i:i + IGDB_BATCH])
            for g in self.query("games", f"fields {IGDB_FIELDS}; where id = ({chunk}); limit 500;"):
                out[g["id"]] = g
        return out


# ------------------------------------------------------------------ 실행


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Steam + IGDB 게임 필수 정보 수집")
    ap.add_argument("--apps", help="스팀 앱 번호 목록 (쉼표로 구분). 없으면 data/catalog_apps.json 전체")
    ap.add_argument("--limit", type=int, default=0, help="앞에서부터 이 개수만 (시험용)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="저장 폴더 (기본 data/collected)")
    ap.add_argument("--refresh", action="store_true", help="캐시를 무시하고 새로 받기")
    ap.add_argument("--no-igdb", action="store_true", help="IGDB 를 쓰지 않고 Steam 정보만")
    ap.add_argument("--top", type=int, default=0, help="Steam 리뷰 수가 많은 인기 게임 N개를 추가 (SteamSpy 목록)")
    ap.add_argument("--top-per-genre", type=int, default=0, help="장르별 인기 게임 N개씩 추가 (SteamSpy 목록)")
    ap.add_argument("--genres", help=f"--top-per-genre 에 쓸 IGDB 장르 이름 (쉼표). 기본: {','.join(DEFAULT_GENRES)}")
    ap.add_argument("--pool-pages", type=int, default=0,
                    help=f"장르별 고르기 후보로 받을 SteamSpy 인기 목록 페이지 수 (1페이지=1,000개, 기본 {GENRE_POOL_PAGES})")
    ap.add_argument("--min-reviews", type=int, default=0, help="인기 게임 목록에서 리뷰가 이 수 미만이면 제외")
    ap.add_argument("--no-catalog", action="store_true", help="프론트 카탈로그 게임은 빼고 인기 게임만")
    ap.add_argument("--no-korean", action="store_true",
                    help="한국어 상점 정보를 받지 않음 (요청이 3번 -> 2번으로 줄어 약 1/3 빨라짐. 이름·설명은 영어)")
    args = ap.parse_args(argv)

    out = Path(args.out)
    cache = Cache(out / ".cache", args.refresh)
    try:
        targets = load_targets(args, cache)
    except HttpError as e:
        sys.exit(f"인기 게임 목록을 만들지 못했습니다 (SteamSpy 또는 IGDB): {e}. 잠시 뒤 다시 실행하세요.")
    if not targets:
        sys.exit("수집할 게임이 없습니다.")
    langs = ["english"] if args.no_korean else ["english", "koreana"]
    todo = sum(1 for app, _ in targets if cache.get(f"steam_{app}_english") is None)
    eta = todo * (len(langs) + 1) * STEAM_DELAY / 60
    print(f"게임 {len(targets)}개 수집 시작 (새로 받을 게임 {todo}개, 예상 약 {eta:.0f}분 이상. "
          f"중간에 꺼도 다시 실행하면 이어서 받습니다. 캐시: {cache.folder})")

    # 1) Steam: 영어(장르·카테고리 원문) + 한국어(이름·설명) + 리뷰 수
    steam: dict[int, tuple] = {}
    failed: list[dict] = []
    conn_fail = 0
    for n, (app, key) in enumerate(targets, 1):
        try:
            en = steam_details(app, "english", cache)
            conn_fail = 0
            if en and en.get("type") and en["type"] != "game":  # DLC·사운드트랙·소프트웨어 등은 추천 대상 아님
                steam[app] = (en, None, None)
                print(f"  [{n}/{len(targets)}] {app} {en.get('name')} (게임 아님: {en['type']}, 제외)")
                continue
            ko = steam_details(app, "koreana", cache) if "koreana" in langs else None
            try:
                rv = steam_reviews(app, cache) if (en or ko) else None  # 상점에 없는 앱은 리뷰도 묻지 않음
            except HttpError as e:  # 리뷰 수만 실패하면 게임 정보는 살리고 리뷰 칸만 비운다
                print(f"  [{n}/{len(targets)}] {app} 리뷰 수 조회 실패: {e}")
                failed.append({"steam_app_id": app, "catalog_key": key, "reason": f"steam reviews {e}"})
                rv = None
        except HttpError as e:
            print(f"  [{n}/{len(targets)}] {app} 스팀 실패: {e}")
            failed.append({"steam_app_id": app, "catalog_key": key, "reason": f"steam {e}"})
            steam[app] = (None, None, None)
            conn_fail = conn_fail + 1 if e.status == 0 else 0
            if conn_fail >= 3:
                sys.exit("스팀에 3번 연속 연결하지 못해 멈춥니다. 인터넷 연결을 확인한 뒤 다시 실행하세요 "
                         "(이미 받은 게임은 건너뜁니다).")
            continue
        steam[app] = (en, ko, rv)
        label = (en or ko or {}).get("name") or "(스팀 상점에 없음)"
        print(f"  [{n}/{len(targets)}] {app} {label}")

    # 게임이 아닌 앱(DLC 등)은 여기서 빼고 보고서에만 남긴다
    not_a_game = [{"steam_app_id": app, "name": steam[app][0].get("name"), "type": steam[app][0].get("type")}
                  for app, _ in targets if steam[app][0] and steam[app][0].get("type") not in (None, "game")]
    skip = {x["steam_app_id"] for x in not_a_game}
    targets = [(app, key) for app, key in targets if app not in skip]

    # 2) IGDB: Steam AppID 로 연결된 게임만 (이름으로는 연결하지 않음)
    igdb_rows: dict[int, dict | None] = {app: None for app, _ in targets}
    env = load_env(ROOT / ".env")
    if args.no_igdb:
        print("IGDB 건너뜀 (--no-igdb)")
    elif not (env.get("IGDB_CLIENT_ID") and env.get("IGDB_CLIENT_SECRET")):
        print("IGDB 키(.env 의 IGDB_CLIENT_ID / IGDB_CLIENT_SECRET)가 없어 Steam 정보만 저장합니다.")
    else:
        cached = cache.get("igdb_by_app")
        if cached is not None and all(str(app) in cached for app, _ in targets):
            igdb_rows = {app: cached[str(app)] for app, _ in targets}
            print("IGDB: 캐시 사용")
        else:
            ig = Igdb(env["IGDB_CLIENT_ID"], env["IGDB_CLIENT_SECRET"])
            try:
                ig.login()
            except HttpError as e:
                ig = None
                print(f"IGDB 로그인(Twitch 토큰 발급) 실패: {e}")
                print("  -> .env 의 IGDB_CLIENT_ID / IGDB_CLIENT_SECRET 값이 Twitch 개발자 콘솔의 값과 같은지 확인하세요. "
                      "Steam 정보만 저장합니다.")
            try:
                if ig is None:
                    raise LookupError
                links = ig.steam_links([app for app, _ in targets])
                games = ig.games([gid for ids in links.values() for gid in ids])
                for app, _ in targets:
                    steam_name = (steam[app][0] or steam[app][1] or {}).get("name")
                    igdb_rows[app] = pick_igdb_match([games[g] for g in links.get(app, []) if g in games], steam_name)
                cache.put("igdb_by_app", {str(a): v for a, v in igdb_rows.items()})
                ok = sum(1 for v in igdb_rows.values() if v)
                print(f"IGDB: {ok}/{len(targets)}개를 Steam AppID 로 연결")
            except LookupError:
                pass
            except HttpError as e:
                print(f"IGDB 게임 조회 실패: {e}. Steam 정보만 저장합니다.")

    # 3) 합치기 + 저장
    records = []
    for app, key in targets:
        en, ko, rv = steam[app]
        ig = igdb_rows[app]
        if not (en or ko or ig):
            failed.append({"steam_app_id": app, "catalog_key": key, "reason": "스팀·IGDB 모두 정보 없음"})
            continue
        records.append(build_record(app, en, ko, rv, ig, key))

    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(records),
        "sources": {"steam": "store.steampowered.com/api/appdetails (l=" + ", l=".join(langs) + "), "
                             "api.steampowered.com/IUserReviewsService/GetAppReviews",
                    "igdb": "api.igdb.com/v4 external_games, games",
                    "target_list": "frontend catalog" + (" + SteamSpy popular" if args.top or args.top_per_genre else "")},
    }
    (out / "games.json").write_text(json.dumps({"meta": meta, "games": records}, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    with open(out / "games.csv", "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: 엑셀에서 한글 안 깨짐
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in records:
            w.writerow(to_csv_row(r))

    report = {
        **meta,
        "failed": failed,
        "igdb_not_linked": [{"steam_app_id": r["steam_app_id"], "name": r["steam_name"]} for r in records if not r["igdb_id"]],
        "not_a_game_excluded": not_a_game,
        "empty_fields": {c: sum(1 for r in records if r.get(c) in (None, "", []))
                         for c in CSV_COLUMNS if c not in ("catalog_key", "name_ko", "igdb_url")},
    }
    (out / "collect_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n완료: {len(records)}개 저장 -> {out / 'games.json'}, {out / 'games.csv'}")
    print(f"확인할 것: {out / 'collect_report.json'} (실패 {len(failed)}개, IGDB 미연결 {len(report['igdb_not_linked'])}개)")


if __name__ == "__main__":
    main()
