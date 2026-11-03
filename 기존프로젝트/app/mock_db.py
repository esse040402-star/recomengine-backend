"""Supabase 없이 백엔드를 돌려보기 위한 메모리 내 가짜 DB.

routers/services 가 쓰는 supabase-py 쿼리 빌더 중 필요한 부분만 흉내 낸다:
  table(...).select(cols, count=) / insert / upsert(on_conflict=) / update / delete
  .eq / .ilike / .contains / .order / .range / .limit / .execute()
  select 안의 임베드("games(id,title)") 와 auth.get_user(token)

서버를 끄면 데이터는 사라진다. 외부 패키지에 의존하지 않는다.
"""
import copy
import hashlib
import hmac
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "mock_games.json"

TABLE_DEFAULTS = {
    "diagnosis_sessions": {"status": "in_progress", "user_id": None, "completed_at": None},
    "games": {"genres": [], "tags": [], "platforms": [], "price_info": {}, "source_data": {}},
    "analysis_reports": {"keywords": [], "generated_by": "ollama"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MockResult:
    def __init__(self, data: list[dict], count: int | None = None):
        self.data = data
        self.count = count


def _split_top_level(text: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


class MockQuery:
    def __init__(self, store: "MockSupabase", table: str):
        self.store, self.table = store, table
        self.op = "select"
        self.columns = "*"
        self.want_count = False
        self.filters: list = []
        self.order_by: tuple[str, bool] | None = None
        self.slice: tuple[int, int] | None = None
        self.max_rows: int | None = None
        self.payload = None
        self.on_conflict = "id"

    # --- 빌더 ---
    def select(self, columns: str = "*", count: str | None = None):
        self.columns, self.want_count = columns, bool(count)
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def upsert(self, payload, on_conflict: str | None = None, **_):
        self.op, self.payload = "upsert", payload
        if on_conflict:
            self.on_conflict = on_conflict
        return self

    def update(self, payload: dict):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def ilike(self, col, pattern: str):
        rx = re.compile("^" + ".*".join(re.escape(p) for p in pattern.split("%")) + "$", re.IGNORECASE | re.DOTALL)
        self.filters.append(lambda r: isinstance(r.get(col), str) and bool(rx.match(r[col])))
        return self

    def contains(self, col, values):
        self.filters.append(lambda r: all(v in (r.get(col) or []) for v in values))
        return self

    def order(self, col, desc: bool = False, **_):
        self.order_by = (col, desc)
        return self

    def range(self, start: int, end: int):
        self.slice = (start, end)
        return self

    def limit(self, n: int):
        self.max_rows = n
        return self

    # --- 실행 ---
    def execute(self) -> MockResult:
        with self.store.lock:
            return getattr(self, f"_{self.op}")()

    def _rows(self) -> list[dict]:
        return self.store.tables.setdefault(self.table, [])

    def _matches(self, row: dict) -> bool:
        return all(f(row) for f in self.filters)

    def _with_defaults(self, row: dict) -> dict:
        out = {"id": str(uuid.uuid4()), "created_at": _now(), **copy.deepcopy(TABLE_DEFAULTS.get(self.table, {}))}
        if self.table == "diagnosis_sessions":
            out["started_at"] = _now()
        out.update(copy.deepcopy(row))
        return out

    def _payload_rows(self) -> list[dict]:
        return self.payload if isinstance(self.payload, list) else [self.payload]

    def _insert(self) -> MockResult:
        created = [self._with_defaults(r) for r in self._payload_rows()]
        self._rows().extend(created)
        return MockResult(copy.deepcopy(created))

    def _upsert(self) -> MockResult:
        keys = [k.strip() for k in self.on_conflict.split(",")]
        out = []
        for incoming in self._payload_rows():
            existing = next(
                (r for r in self._rows() if all(r.get(k) is not None and r.get(k) == incoming.get(k) for k in keys)),
                None,
            )
            if existing:
                existing.update(copy.deepcopy(incoming))
                out.append(copy.deepcopy(existing))
            else:
                row = self._with_defaults(incoming)
                self._rows().append(row)
                out.append(copy.deepcopy(row))
        return MockResult(out)

    def _update(self) -> MockResult:
        out = []
        for r in self._rows():
            if self._matches(r):
                r.update(copy.deepcopy(self.payload))
                out.append(copy.deepcopy(r))
        return MockResult(out)

    def _delete(self) -> MockResult:
        keep, gone = [], []
        for r in self._rows():
            (gone if self._matches(r) else keep).append(r)
        self.store.tables[self.table] = keep
        return MockResult(copy.deepcopy(gone))

    def _select(self) -> MockResult:
        rows = [r for r in self._rows() if self._matches(r)]
        total = len(rows)
        if self.order_by:
            col, desc = self.order_by
            rows.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if self.slice:
            rows = rows[self.slice[0] : self.slice[1] + 1]
        if self.max_rows is not None:
            rows = rows[: self.max_rows]
        return MockResult([self._project(r) for r in rows], total if self.want_count else None)

    def _project(self, row: dict) -> dict:
        if self.columns.strip() == "*":
            return copy.deepcopy(row)
        out: dict = {}
        for part in _split_top_level(self.columns):
            m = re.fullmatch(r"(\w+)\((.*)\)", part, re.DOTALL)
            if m:  # 임베드: recommendations.game_id -> games
                name, inner = m.group(1), m.group(2)
                fk = name[:-1] + "_id" if name.endswith("s") else name + "_id"
                target = next((g for g in self.store.tables.get(name, []) if g.get("id") == row.get(fk)), None)
                sub = MockQuery(self.store, name)
                sub.columns = inner
                out[name] = sub._project(target) if target else None
            elif part in row:
                out[part] = copy.deepcopy(row[part])
        return out


class MockAuth:
    """supabase-py auth 흉내.
    - get_user("mock-<이름>") : Bearer mock 토큰
    - admin.create_user / sign_in_with_password : 회원가입/로그인 (비밀번호는 PBKDF2 해시로만 저장)"""

    def __init__(self):
        self.users: dict[str, dict] = {}  # email -> {id, email, name, salt, hash}
        self.admin = SimpleNamespace(create_user=self._create_user)

    @staticmethod
    def _hash(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 20_000).hex()

    def _create_user(self, attrs: dict):
        email = attrs["email"].strip().lower()
        if email in self.users:
            raise ValueError("A user with this email address has already been registered")
        salt = os.urandom(16)
        user = {"id": str(uuid.uuid4()), "email": email, "salt": salt,
                "hash": self._hash(attrs["password"], salt), "meta": dict(attrs.get("user_metadata") or {})}
        self.users[email] = user
        return SimpleNamespace(user=self._public(user))

    def sign_in_with_password(self, creds: dict):
        user = self.users.get(creds["email"].strip().lower())
        if not user or not hmac.compare_digest(user["hash"], self._hash(creds["password"], user["salt"])):
            raise ValueError("Invalid login credentials")
        return SimpleNamespace(user=self._public(user))

    @staticmethod
    def _public(user: dict):
        return SimpleNamespace(id=user["id"], email=user["email"], user_metadata=dict(user["meta"]))

    def get_user(self, token: str):
        if not token or not token.startswith("mock-") or len(token) <= 5:
            raise ValueError("mock 모드에서는 'mock-<이름>' 형식의 토큰만 사용할 수 있습니다.")
        return SimpleNamespace(user=SimpleNamespace(id=token[5:]))


class MockSupabase:
    def __init__(self, seed: bool = True):
        self.lock = threading.RLock()
        self.tables: dict[str, list[dict]] = {}
        self.auth = MockAuth()
        if seed:
            self._seed_games()

    def table(self, name: str) -> MockQuery:
        return MockQuery(self, name)

    def _seed_games(self) -> None:
        if not SEED_FILE.exists():
            return
        rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        for r in rows:
            q = MockQuery(self, "games")
            q.payload = {**r, "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "mock-game:" + r["title"]))}
            q.on_conflict = "id"
            q._upsert()
