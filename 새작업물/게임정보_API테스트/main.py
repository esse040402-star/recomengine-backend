"""독립 게임정보 조회 서버. 기존 프로젝트를 import하지 않습니다."""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI(title='RecomEngine 게임정보 API', version='1.0.0')
STEAM_KEY = os.getenv('STEAM_API_KEY', '').strip()
CLIENT_ID = os.getenv('IGDB_CLIENT_ID', '').strip()
CLIENT_SECRET = os.getenv('IGDB_CLIENT_SECRET', '').strip()
client = httpx.Client(timeout=25, follow_redirects=True)
lock = threading.RLock()
igdb_lock = threading.Lock()
catalog = {}
sync_state = {'running': False, 'complete': False, 'count': 0, 'error': None}
cache = {}
token = {'value': '', 'expires': 0}
last_igdb = 0.0


def request(method, url, **kwargs):
    # 예외에 요청 URL이나 인증키를 포함하지 않습니다.
    for attempt in range(3):
        try:
            response = client.request(method, url, **kwargs)
        except httpx.RequestError:
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise HTTPException(502, '외부 서비스 연결 실패. 잠시 후 다시 조회해 주세요.')
        if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
            time.sleep(attempt + 1)
            continue
        if response.status_code >= 400:
            raise HTTPException(502, f'외부 서비스 HTTP {response.status_code}. 키 또는 호출 제한을 확인하세요.')
        return response


def as_json(response):
    try:
        return response.json()
    except ValueError:
        raise HTTPException(502, '외부 서비스가 JSON 대신 다른 응답을 반환했습니다.')


def cached(key, loader, seconds=900):
    with lock:
        entry = cache.get(key)
        if entry and entry[0] > time.monotonic():
            return entry[1]
    result = loader()
    with lock:
        if len(cache) >= 300:
            cache.pop(next(iter(cache)))
        cache[key] = (time.monotonic() + seconds, result)
    return result


def sync_catalog():
    try:
        cursor = 0
        new = {}
        while True:
            data = as_json(request('GET', 'https://api.steampowered.com/IStoreService/GetAppList/v1/',
                params={'key': STEAM_KEY, 'input_json': json.dumps({'include_games': True,
                'include_dlc': False, 'include_software': False, 'include_videos': False,
                'include_hardware': False, 'max_results': 10000, 'last_appid': cursor})}))
            body = data.get('response', {})
            apps = body.get('apps')
            if not isinstance(apps, list):
                raise HTTPException(502, 'Steam 게임 목록 응답 형식이 올바르지 않습니다.')
            for game in apps:
                new[int(game['appid'])] = {'appid': int(game['appid']), 'name': game.get('name', '')}
            with lock:
                catalog.update(new)
                sync_state['count'] = len(catalog)
            if not body.get('have_more_results', False):
                with lock:
                    catalog.clear()
                    catalog.update(new)
                    sync_state.update(complete=True, count=len(new))
                break
            next_cursor = int(body.get('last_appid') or (apps[-1]['appid'] if apps else cursor))
            if next_cursor <= cursor:
                raise HTTPException(502, 'Steam 목록 페이지가 진행되지 않았습니다.')
            cursor = next_cursor
            time.sleep(0.35)
    except Exception as exc:
        with lock:
            sync_state['error'] = exc.detail if isinstance(exc, HTTPException) else '목록 수집 오류. 다시 시도해 주세요.'
    finally:
        with lock:
            sync_state['running'] = False


def start_sync():
    if not STEAM_KEY:
        raise HTTPException(503, '전체 게임 목록을 가져오려면 STEAM_API_KEY를 등록하세요.')
    with lock:
        if not sync_state['running'] and not sync_state['complete']:
            sync_state.update(running=True, error=None)
            threading.Thread(target=sync_catalog, daemon=True).start()
        return dict(sync_state)


def igdb(endpoint, query):
    global last_igdb
    if not (CLIENT_ID and CLIENT_SECRET):
        raise HTTPException(503, 'IGDB_CLIENT_ID와 IGDB_CLIENT_SECRET을 등록하세요.')
    with igdb_lock:
        if token['expires'] <= time.monotonic():
            data = as_json(request('POST', 'https://id.twitch.tv/oauth2/token', data={
                'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'client_credentials'}))
            token.update(value=data['access_token'], expires=time.monotonic() + max(0, int(data['expires_in']) - 60))
        time.sleep(max(0, 0.3 - (time.monotonic() - last_igdb)))
        last_igdb = time.monotonic()
        try:
            return as_json(request('POST', f'https://api.igdb.com/v4/{endpoint}',
                headers={'Client-ID': CLIENT_ID, 'Authorization': 'Bearer ' + token['value']}, content=query))
        except HTTPException as exc:
            if '401' in str(exc.detail):
                token['expires'] = 0
            raise


def igdb_detail(appid):
    sources = cached('igdb_sources', lambda: igdb('external_game_sources', 'fields name; limit 500;'), 86400)
    source = next((x['id'] for x in sources if x.get('name', '').lower() == 'steam'), None)
    if source is None:
        raise HTTPException(502, 'IGDB에서 Steam 분류를 찾지 못했습니다.')
    matches = igdb('external_games', f'fields game; where external_game_source = {source} & uid = "{appid}"; limit 1;')
    if not matches:
        return {'status': 'not_found', 'message': 'Steam AppID에 대응하는 IGDB 게임이 없습니다.'}
    gid = int(matches[0]['game'])
    games = igdb('games', f'fields name,summary,genres.name,themes.name,keywords.name,game_modes.name,player_perspectives.name,platforms.name,rating,rating_count,total_rating,first_release_date; where id = {gid};')
    times = igdb('game_time_to_beats', f'fields normally,hastily,completely,count; where game_id = {gid};')
    return {'status': 'ok', 'game': games[0] if games else None, 'time_to_beat_seconds': times}


def tags(appid):
    html = request('GET', f'https://store.steampowered.com/app/{appid}/', params={'l': 'english'},
        cookies={'birthtime': '0', 'lastagecheckage': '1-0-1990'}).text
    soup = BeautifulSoup(html, 'html.parser')
    result = []
    for a in soup.select('a.app_tag'):
        label = a.get_text(' ', strip=True)
        if label and label not in result:
            result.append(label)
    return {'status': 'ok' if result else 'unavailable', 'values': result,
            'source': 'Steam 상점 HTML의 사용자 태그 (공식 Web API가 아님)'}


def safe_part(fn):
    try:
        return fn()
    except HTTPException as exc:
        return {'status': 'error', 'message': exc.detail}
    except Exception:
        return {'status': 'error', 'message': '외부 응답을 처리하지 못했습니다.'}


@app.get('/')
def home():
    return FileResponse(Path(__file__).with_name('index.html'))


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/api/status')
def status():
    with lock:
        return {'keys': {'steam': bool(STEAM_KEY), 'igdb': bool(CLIENT_ID and CLIENT_SECRET)},
                'catalog': dict(sync_state), 'storage': '메모리 캐시 — 서버 재시작 시 다시 수집'}


@app.post('/api/catalog/sync')
def sync():
    return start_sync()


@app.get('/api/games')
def search(q: str = Query('', max_length=100), page: int = Query(1, ge=1), size: int = Query(30, ge=1, le=100)):
    start_sync()
    with lock:
        rows = [g for g in catalog.values() if q.casefold() in g['name'].casefold() or q == str(g['appid'])]
        rows.sort(key=lambda g: g['appid'])
        return {'items': rows[(page-1)*size:page*size], 'total': len(rows), 'page': page, 'size': size,
                'catalog': dict(sync_state)}


@app.get('/api/games/{appid}')
def detail(appid: int):
    if not 1 <= appid <= 4294967295:
        raise HTTPException(422, '올바른 Steam AppID를 입력하세요.')
    def load():
        raw = as_json(request('GET', 'https://store.steampowered.com/api/appdetails',
            params={'appids': appid, 'cc': 'kr', 'l': 'korean'}))
        item = raw.get(str(appid), {})
        if not item.get('success'):
            raise HTTPException(404, '이 AppID의 상점 정보를 조회할 수 없습니다.')
        data = item['data']
        with ThreadPoolExecutor(max_workers=3) as pool:
            tag_job = pool.submit(safe_part, lambda: tags(appid))
            review_job = pool.submit(safe_part, lambda: as_json(request('GET',
                f'https://store.steampowered.com/appreviews/{appid}', params={'json': 1, 'language': 'all', 'num_per_page': 5})))
            igdb_job = pool.submit(safe_part, lambda: igdb_detail(appid))
            return {'appid': appid, 'steam': data, 'steam_tags': tag_job.result(),
                    'reviews': review_job.result(), 'igdb': igdb_job.result(),
                    'notes': ['장르·카테고리·사용자 태그는 별도 분류입니다.',
                    '사양은 Steam 원문입니다. 고사양/저사양 등급을 임의로 만들지 않습니다.',
                    'IGDB 클리어 시간은 초 단위이며 모든 게임에 제공되지는 않습니다.']}
    return cached(('detail', appid), load)
