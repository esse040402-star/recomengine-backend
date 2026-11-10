import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as m
from fastapi.testclient import TestClient
import httpx

c = TestClient(m.app)

def setup_function():
    m.cache.clear()
    m.catalog.clear()
    m.sync_state.update(running=False, complete=False, count=0, error=None)

def test_boot_without_keys(monkeypatch):
    monkeypatch.setattr(m, 'STEAM_KEY', '')
    assert c.get('/').status_code == 200
    assert c.get('/health').json() == {'status': 'ok'}
    assert c.get('/api/games').status_code == 503
    assert c.get('/api/status').json()['keys']['steam'] is False

def test_full_catalog_pagination(monkeypatch):
    calls = []
    def fake(method, url, **kwargs):
        cursor = json.loads(kwargs['params']['input_json'])['last_appid']
        calls.append(cursor)
        return httpx.Response(200, json={'response': {'apps': [{'appid': cursor+10, 'name': 'Game'}],
            'have_more_results': cursor == 0, 'last_appid': cursor+10}})
    monkeypatch.setattr(m, 'request', fake)
    m.sync_catalog()
    assert calls == [0, 10]
    assert set(m.catalog) == {10, 20}
    assert m.sync_state['complete'] is True

def test_stalled_pagination(monkeypatch):
    monkeypatch.setattr(m, 'request', lambda *a, **k: httpx.Response(200,json={'response': {'apps': [], 'have_more_results': True}}))
    m.sync_catalog()
    assert m.sync_state['error']
    assert not m.sync_state['complete']

def test_detail_preserves_data_and_partial_failure(monkeypatch):
    monkeypatch.setattr(m, 'request', lambda *a, **k: httpx.Response(200,json={'42': {'success': True,'data': {'name': 'Test', 'genres': [{'id':'1','description':'Action'}]}}}))
    monkeypatch.setattr(m, 'tags', lambda x: {'values': ['Open World'], 'status':'ok'})
    monkeypatch.setattr(m, 'CLIENT_ID', '')
    result = c.get('/api/games/42')
    assert result.status_code == 200
    d=result.json()
    assert d['steam']['genres'][0]['id'] == '1'
    assert d['steam_tags']['values'] == ['Open World']
    assert d['igdb']['status'] == 'error'

def test_validation():
    assert c.get('/api/games/-1').status_code == 422
    assert c.get('/api/games?page=0').status_code == 422

def test_errors_hide_key(monkeypatch):
    def fake(*a, **k):
        raise httpx.ConnectError('secret=DO_NOT_EXPOSE')
    monkeypatch.setattr(m.client, 'request', fake)
    monkeypatch.setattr(m.time, 'sleep', lambda x: None)
    response=c.get('/api/games/42')
    assert response.status_code == 502
    assert 'DO_NOT_EXPOSE' not in response.text

def test_tag_extraction(monkeypatch):
    monkeypatch.setattr(m, 'request', lambda *a, **k: httpx.Response(200,text='<a class="app_tag">RPG</a><a class="app_tag">RPG</a><a class="app_tag">Open World</a>'))
    assert m.tags(42)['values'] == ['RPG', 'Open World']

def test_igdb_matches_steam_id_not_name(monkeypatch):
    queries=[]
    def fake(endpoint, query):
        queries.append((endpoint,query))
        if endpoint=='external_game_sources': return [{'id':1,'name':'Steam'}]
        if endpoint=='external_games': return [{'game':99}]
        if endpoint=='games': return [{'id':99,'name':'Matched'}]
        return [{'normally':7200,'count':12}]
    monkeypatch.setattr(m,'igdb',fake)
    result=m.igdb_detail(42)
    assert 'uid = "42"' in queries[1][1]
    assert result['game']['id']==99
    assert result['time_to_beat_seconds'][0]['normally']==7200
