"""Match survey codes against Steam metadata and the team's curated labels."""
import json
import re
from pathlib import Path

SEED = Path(__file__).parent / 'data/catalog.json'
CACHE = SEED.parents[2] / 'results/steam_details_cache.json'
GENRES = {'액션':'genre:action','전략':'genre:strategy','어드벤처':'genre:adventure',
          '시뮬레이션':'genre:simulation','퍼즐':'tag:puzzle','스토리':'tag:story_rich'}
CATEGORIES = {2:'category:single_player',9:'category:co_op',38:'category:co_op',
              39:'category:co_op',49:'category:pvp',36:'category:pvp',37:'category:pvp'}
RISKS = {'complex':'preference:complexity','motion':'preference:motion_intensity',
         'difficulty':'tag:difficult','grind':'tag:grindy','pvp':'category:pvp'}
VISUAL = {'real':'tag:realistic','realistic':'tag:realistic','anime':'tag:anime',
          'pixel':'tag:pixel_graphics','casual':'tag:cute'}
SOCIAL = {'solo':'category:single_player','coop':'category:co_op','pvp':'category:pvp'}

def features(game, details):
    genres=set(details.get('genres',game['steamGenres']))
    codes={GENRES.get(k) for k in genres}
    codes.update(CATEGORIES.get(k) for k in details.get('categoryIds',game['categories']))
    if game['classification']=='curated':
        codes.update(GENRES.get(k) for k in game['genres'])
        codes.update(RISKS.get(k) for k in game['risks'])
        codes.update(SOCIAL.get(k) for k in game['social'])
        codes.add(VISUAL.get(game['visual']))
        if game['session']: codes.add('session:'+game['session'])
    if 'genre:action' in codes: codes.add('tag:action')
    # Conservative proxy: explicitly low RAM AND explicitly supported integrated GPU.
    spec={str(k).lower():str(v).lower() for k,v in details.get('minimum',[])}
    ram=re.search(r'(\d+(?:\.\d+)?)\s*gb',spec.get('메모리',spec.get('memory','')))
    gpu=spec.get('그래픽',spec.get('graphics',''))
    if ram and float(ram[1])<=4 and re.search(r'intel.*(?:hd|uhd)|integrated graphics',gpu):
        codes.add('hardware:low_spec')
    return codes-{None}

def recommend(weights, constraints, rows=None, updates=None):
    if rows is None: rows=json.loads(SEED.read_text(encoding='utf-8'))
    if updates is None:
        updates=json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {}
    candidates=[]
    for g in rows:
        live=updates.get(g['id'])
        d=live if live is not None else g['details']
        platforms=set(g['platforms'] or [])
        if 'os' in d:
            platforms.discard('pc')
            if any(d['os'].values()): platforms.add('pc')
        if constraints['platforms'] and not platforms.intersection(constraints['platforms']):continue
        codes=features(g,d)
        hits={k:v for k,v in weights.items() if k in codes and v}
        score=sum(hits.values())
        if score<=0:continue
        candidates.append(dict(app_id=g['app'],game_id=g['id'],title=g['title'],score=score,
                               matched_weights=hits,price=d.get('price'),checked_at=d.get('checkedAt'),
                               detail_source='team_api' if live is not None else 'snapshot'))
    candidates.sort(key=lambda g:(-g['score'],g['app_id']))
    return {'status':'matched' if candidates else 'no_match','games':candidates[:5]}
