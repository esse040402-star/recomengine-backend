"""프로토타입 HTML의 /api/survey/generate 요청(2곳)에 blueprint 를 추가해 backend/frontend/index.html 로 저장한다.
서버가 28문항 구조를 알아야 AI가 문장을 다듬을 수 있는데, 프론트가 보내주는 E.publicBlueprint() 결과가 유일한 출처다.
(프론트 담당자가 직접 고친다면 아래 한 줄만 추가하면 된다:  blueprint:E.publicBlueprint(<track>,<answers>),  )

실행 (backend 폴더에서):
  python -m scripts.patch_frontend "C:\\경로\\화면_프로토타입_진.html"
"""
import re
import sys
from pathlib import Path

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
