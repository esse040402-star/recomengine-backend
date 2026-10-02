"""Swagger 한국어 설명이 빠짐없이 붙어 있는지 소스 코드를 읽어서 검사한다 (fastapi 불필요).
새 API를 추가하고 설명을 깜빡하면 여기서 바로 알려준다.   python -m tests.test_docs_coverage"""
import ast
import re
from pathlib import Path

from app import docs

ROOT = Path(__file__).resolve().parent.parent / "app"
HANGUL = re.compile(r"[가-힣]")
METHODS = {"get", "post", "put", "delete", "patch"}


def _route_calls():
    for path in sorted((ROOT / "routers").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            for dec in fn.decorator_list:
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and isinstance(dec.func.value, ast.Name) and dec.func.value.id == "router"
                        and dec.func.attr in METHODS):
                    yield path.name, fn.name, dec


def _doc_key(call: ast.Call) -> str | None:
    for kw in call.keywords:  # **docs.doc("키")
        if kw.arg is None and isinstance(kw.value, ast.Call):
            c = kw.value
            if isinstance(c.func, ast.Attribute) and c.func.attr == "doc" and c.args and isinstance(c.args[0], ast.Constant):
                return c.args[0].value
    return None


def test_every_endpoint_uses_a_korean_doc():
    used = []
    for file, fn, call in _route_calls():
        key = _doc_key(call)
        assert key, f"{file}:{fn} 에 **docs.doc(\"키\") 설명이 없습니다"
        assert key in docs.DOCS, f"{file}:{fn} 의 설명 키 '{key}' 가 docs.py 에 없습니다"
        used.append(key)
    assert len(used) == len(set(used)), "같은 설명을 두 엔드포인트가 쓰고 있습니다"
    assert set(used) == set(docs.DOCS), f"어디서도 쓰지 않는 설명: {set(docs.DOCS) - set(used)}"
    assert len(used) == 22


def test_docs_are_korean_and_complete():
    for key, d in docs.DOCS.items():
        assert HANGUL.search(d["summary"]) and "(" in d["summary"] and d["summary"].endswith(")"), f"{key}: 제목은 'English (한국어)' 형태"
        assert HANGUL.search(d["description"]) and len(d["description"]) > 30, f"{key}: 설명이 너무 짧음"
        ok = [c for c in d["responses"] if c < 300]
        assert len(ok) == 1 and "content" in d["responses"][ok[0]] and d["responses"][ok[0]]["description"], f"{key}: 성공 응답 예시 필요"
        for code, r in d["responses"].items():
            assert HANGUL.search(r["description"]), f"{key}: {code} 설명이 한국어가 아님"


def test_tags_have_korean_descriptions():
    tag_names = [t["name"] for t in docs.OPENAPI_TAGS]
    assert len(tag_names) == len(set(tag_names)) == 6
    for t in docs.OPENAPI_TAGS:
        assert HANGUL.search(t["name"]) and HANGUL.search(t["description"])
    declared = set()
    for path in (ROOT / "routers").glob("*.py"):
        declared |= set(re.findall(r"tags=\[docs\.(\w+)\]", path.read_text(encoding="utf-8")))
    assert {getattr(docs, n) for n in declared} == set(tag_names)


def test_request_fields_have_descriptions():
    for file in (ROOT / "schemas.py", ROOT / "routers" / "account.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for stmt in cls.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id != "model_config":
                    v = stmt.value
                    ok = isinstance(v, ast.Call) and getattr(v.func, "id", "") == "Field" and any(k.arg == "description" for k in v.keywords)
                    assert ok, f"{file.name}: {cls.name}.{stmt.target.id} 에 Field(description=...) 가 없습니다"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
