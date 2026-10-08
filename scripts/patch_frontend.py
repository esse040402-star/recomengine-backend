"""[사용 중단 · 2026-10-09] 예전 '단일 HTML 프로토타입'용 스크립트입니다.

React 프론트(frontend/)는 /api/survey/generate 에 blueprint 를 이미 보내므로 패치가 필요 없고,
이 스크립트는 결과를 frontend/index.html 에 저장하기 때문에 **실행하면 React 진입 파일(index.html)을 덮어씁니다.**
그래서 실행하면 바로 멈추도록 막아 두었습니다. 화면을 보는 방법은 README.md 의 '6단계' 를 참고하세요.

(참고용 설명) 프로토타입 HTML의 /api/survey/generate 요청(2곳)에 blueprint 를 추가해 backend/frontend/index.html 로 저장하던 코드입니다.
서버가 28문항 구조를 알아야 AI가 문장을 다듬을 수 있는데, 프론트가 보내주는 E.publicBlueprint() 결과가 유일한 출처다.
"""
import re
import sys
from pathlib import Path

sys.exit("이 스크립트는 더 이상 쓰지 않습니다. React 프론트는 blueprint 를 이미 보내고, 실행하면 frontend/index.html 을 덮어씁니다. "
         "화면 실행 방법은 README.md 의 '6단계' 를 보세요.")

# body:JSON.stringify({track:<식>,answers:<식>   ->   body:JSON.stringify({blueprint:E.publicBlueprint(<식>,<식>),track:<식>,answers:<식>
PATTERN = re.compile(r"body:JSON\.stringify\(\{track:([\w.]+),answers:([\w.()]+)")

if len(sys.argv) != 2:
    sys.exit("사용법: python -m scripts.patch_frontend <원본 html 경로>")

src = Path(sys.argv[1])
html = src.read_text(encoding="utf-8")
if "/api/survey/generate" not in html:
    sys.exit("/api/survey/generate 호출을 찾지 못했습니다. 다른 파일이 아닌지 확인하세요.")
if "blueprint:E.publicBlueprint" in html:
    sys.exit("이미 blueprint 가 들어 있는 파일입니다.")

patched, n = PATTERN.subn(lambda m: f"body:JSON.stringify({{blueprint:E.publicBlueprint({m[1]},{m[2]}),track:{m[1]},answers:{m[2]}", html)
expected = html.count("/api/survey/generate")
if n != expected:
    sys.exit(f"호출 {expected}곳 중 {n}곳만 패치할 수 있었습니다. 프론트 코드가 바뀌었는지 확인하세요. 중단합니다.")

dst = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
dst.parent.mkdir(exist_ok=True)
dst.write_text(patched, encoding="utf-8")
print(f"{n}곳 패치 완료 -> {dst}")
