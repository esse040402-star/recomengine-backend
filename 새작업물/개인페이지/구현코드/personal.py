"""Personal-page persistence. Guest ownership is supplied by the HTTP adapter.
Replace owner resolution with authenticated user ID when integrating login.
"""
import json
import sqlite3
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timezone

THEMES={'brand':'RecomEngine','elden':'황금빛 판타지','cyber':'네온 도시','stardew':'초록 농장','ocean':'푸른 바다','baldur':'Baldur’s Gate 3','unpacking':'Unpacking'}
class PersonalStore:
    def __init__(self,path,catalog):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.catalog={g['id']:dict(g) for g in catalog}
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS accounts(owner TEXT PRIMARY KEY,nickname TEXT NOT NULL DEFAULT '플레이어',bio TEXT NOT NULL DEFAULT '',theme TEXT NOT NULL DEFAULT 'brand',active TEXT);
            CREATE TABLE IF NOT EXISTS activity(owner TEXT,game TEXT,kind TEXT,updated TEXT,PRIMARY KEY(owner,game,kind));
            CREATE TABLE IF NOT EXISTS surveys(id TEXT PRIMARY KEY,owner TEXT NOT NULL,data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,owner TEXT NOT NULL,name TEXT NOT NULL,survey TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(owner,survey));''')
            if 'avatar' not in [r[1] for r in db.execute('PRAGMA table_info(accounts)')]:db.execute("ALTER TABLE accounts ADD COLUMN avatar TEXT NOT NULL DEFAULT 'Gamepad2'")
            for col,default in [('cover_y',50),('cover_shade',45)]:
                if col not in [r[1] for r in db.execute('PRAGMA table_info(accounts)')]:db.execute(f'ALTER TABLE accounts ADD COLUMN {col} INTEGER NOT NULL DEFAULT {default}')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row;return db
    def ensure(self,db,owner):db.execute('INSERT OR IGNORE INTO accounts(owner) VALUES(?)',(owner,))
    def record_survey(self,owner,data):
        with self.connect() as db:
            row=db.execute('SELECT owner FROM surveys WHERE id=?',(data['result_id'],)).fetchone()
            if row and row['owner']!=owner:raise ValueError('다른 사용자의 설문입니다.')
            db.execute('INSERT OR IGNORE INTO surveys VALUES(?,?,?)',(data['result_id'],owner,json.dumps(data,ensure_ascii=False)))
    def owns_survey(self,owner,rid):
        with self.connect() as db:return bool(db.execute('SELECT 1 FROM surveys WHERE owner=? AND id=?',(owner,rid)).fetchone())
    def state(self,owner):
        with self.connect() as db:
            self.ensure(db,owner)
            settings=dict(db.execute('SELECT nickname,bio,theme,active,avatar,cover_y,cover_shade FROM accounts WHERE owner=?',(owner,)).fetchone())
            surveys=[json.loads(r['data']) for r in db.execute('SELECT data FROM surveys WHERE owner=? ORDER BY rowid DESC',(owner,))]
            profiles=[]
            for r in db.execute('SELECT * FROM profiles WHERE owner=? ORDER BY created',(owner,)):
                item=dict(r);item.pop('owner');data=next(s for s in surveys if s['result_id']==item['survey']);item.update(summary=data['summary'],weights=data['weights']);profiles.append(item)
            activity={kind:[dict(self.catalog[r['game']],updated=r['updated']) for r in db.execute('SELECT game,updated FROM activity WHERE owner=? AND kind=? ORDER BY updated DESC',(owner,kind)) if r['game'] in self.catalog] for kind in ('recent','wishlist')}
            return dict(settings=settings,profiles=profiles,surveys=[{'id':s['result_id'],'title':s['summary']['title']} for s in surveys],themes=THEMES,**activity)
    def update(self,owner,action,payload):
        if not isinstance(payload,dict):raise ValueError('JSON 객체가 필요합니다.')
        now=datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            self.ensure(db,owner)
            if action=='settings':
                name=payload.get('nickname');bio=payload.get('bio','');theme=payload.get('theme')
                if not isinstance(name,str) or not 1<=len(name.strip())<=30 or not isinstance(bio,str) or len(bio)>200 or not isinstance(theme,str) or theme not in THEMES:raise ValueError('닉네임 1~30자, 소개 200자 이내, 제공된 테마를 선택해주세요.')
                avatar=payload.get('avatar','Gamepad2')
                if not isinstance(avatar,str) or avatar not in ('Rocket','Gamepad2','Orbit','Sparkles','ScanFace','Trophy'):raise ValueError('아이콘 오류')
                y=payload.get('cover_y',50);shade=payload.get('cover_shade',45)
                if type(y) is not int or not 0<=y<=100 or type(shade) is not int or not 15<=shade<=80:raise ValueError('배경 설정 범위 오류')
                db.execute('UPDATE accounts SET nickname=?,bio=?,theme=?,avatar=?,cover_y=?,cover_shade=? WHERE owner=?',(name.strip(),bio,theme,avatar,y,shade,owner))
            elif action in ('recent','wishlist'):
                game=payload.get('game')
                if not isinstance(game,str) or game not in self.catalog:raise ValueError('등록되지 않은 게임입니다.')
                if action=='wishlist' and not isinstance(payload.get('saved'),bool):raise ValueError('saved는 true/false로 보내주세요.')
                if action=='wishlist' and not payload['saved']:db.execute('DELETE FROM activity WHERE owner=? AND game=? AND kind=?',(owner,game,action))
                else:db.execute('INSERT OR REPLACE INTO activity VALUES(?,?,?,?)',(owner,game,action,now))
                if action=='recent':db.execute("DELETE FROM activity WHERE owner=? AND kind='recent' AND game NOT IN (SELECT game FROM activity WHERE owner=? AND kind='recent' ORDER BY updated DESC LIMIT 20)",(owner,owner))
            elif action=='profiles':
                name=payload.get('name');survey=payload.get('survey')
                if not isinstance(name,str) or not 1<=len(name.strip())<=30:raise ValueError('프로필명은 1~30자입니다.')
                if not db.execute('SELECT 1 FROM surveys WHERE id=? AND owner=?',(survey,owner)).fetchone():raise ValueError('이 브라우저에서 완료한 설문을 선택해주세요.')
                if db.execute('SELECT 1 FROM profiles WHERE owner=? AND survey=?',(owner,survey)).fetchone():raise ValueError('이미 프로필로 만든 설문입니다. 새 설문을 진행해주세요.')
                pid=str(uuid4());db.execute('INSERT INTO profiles VALUES(?,?,?,?,?)',(pid,owner,name.strip(),survey,now))
                db.execute('UPDATE accounts SET active=? WHERE owner=?',(pid,owner))
            elif action=='active':
                pid=payload.get('id')
                if not db.execute('SELECT 1 FROM profiles WHERE id=? AND owner=?',(pid,owner)).fetchone():raise ValueError('프로필을 찾을 수 없습니다.')
                db.execute('UPDATE accounts SET active=? WHERE owner=?',(pid,owner))
            else:raise ValueError('지원하지 않는 작업입니다.')
        return self.state(owner)
