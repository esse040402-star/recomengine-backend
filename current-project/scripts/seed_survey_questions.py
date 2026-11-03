"""data/survey_questions.json (프로토타입 설문 60문항)을 survey_questions 테이블에 넣는다.

실행 (backend 폴더에서):  python -m scripts.seed_survey_questions
여러 번 실행해도 id 기준으로 덮어쓰므로 안전하다.
"""
import json
from pathlib import Path

from app.db import get_supabase

DATA = Path(__file__).resolve().parent.parent / "data" / "survey_questions.json"


def main() -> None:
    rows = json.loads(DATA.read_text(encoding="utf-8"))
    sb = get_supabase()
    for i in range(0, len(rows), 30):
        sb.table("survey_questions").upsert(rows[i : i + 30], on_conflict="id").execute()
    print(f"survey_questions {len(rows)}건 저장 완료")


if __name__ == "__main__":
    main()
