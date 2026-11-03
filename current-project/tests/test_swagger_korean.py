"""/docs 화면의 영어 고정 문구 한국어 번역 스크립트(app/static/swagger_ko.js) 검사.
번역 규칙은 Node.js가 있을 때만 실행하고, 없으면 건너뜁니다.   python -m tests.test_swagger_korean"""
import json
import re
import shutil
import subprocess
from pathlib import Path

JS = Path(__file__).resolve().parent.parent / "app" / "static" / "swagger_ko.js"
MAIN = Path(__file__).resolve().parent.parent / "app" / "main.py"


def test_script_is_safe_to_inline_and_wired():
    src = JS.read_text(encoding="utf-8")
    assert "</script" not in src.lower()          # <script> 안에 그대로 넣기 때문
    for label in ("Parameters", "Execute", "Responses", "Response body", "Example Value", "Schema", "Request duration"):
        assert f'"{label}":' in src, f"{label} 번역이 없습니다"
    main = MAIN.read_text(encoding="utf-8")
    assert "docs_url=None" in main and '@app.get("/docs", include_in_schema=False)' in main and "swagger_ko.js" in main


def test_translation_rules_with_node():
    node = shutil.which("node")
    if not node:
        print("SKIP: Node.js 가 없어 번역 규칙 실행 테스트를 건너뜁니다")
        return
    cases = {
        "Parameters": "Parameters (입력값)", "  Execute ": "  Execute (실행) ", "string($uuid)": "string($uuid) (문자열)",
        "array[string]": "array[string] (목록)", "(query)": "(query · 주소 뒤 ? 에 붙는 값)",
        " header.": " header. (받을 응답 형식 설정 · 그대로 두세요)",
        "Parameters (입력값)": None, "stringify": None, "toString": None, "application/json": None, "": None,
    }
    script = (f"const {{translate, LABELS}} = require({json.dumps(str(JS))});"
              f"const cases = {json.dumps(cases, ensure_ascii=False)};"
              "const out = {}; for (const k in cases) out[k] = translate(k);"
              "const again = Object.values(LABELS).filter(v => translate(v) !== null);"
              "console.log(JSON.stringify({out, again}));")
    res = subprocess.run([node, "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
    data = json.loads(res.stdout)
    assert data["out"] == cases
    assert data["again"] == []  # 이미 번역한 글자에 또 붙지 않음
    assert all(re.search(r"[가-힣]", v) for v in cases.values() if v)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
