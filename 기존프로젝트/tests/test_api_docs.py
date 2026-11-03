"""실제 서버가 만드는 /docs(OpenAPI)에 한국어 설명이 들어갔는지 확인.  pytest 로 실행 (fastapi, httpx 필요)."""
import os
import re

os.environ["USE_MOCK_DB"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.main import app

HANGUL = re.compile(r"[가-힣]")


@pytest.fixture(scope="module")
def spec():
    with TestClient(app) as c:
        page = c.get("/docs")
        assert page.status_code == 200 and "swagger-ui" in page.text
        assert "Parameters (입력값)" in page.text  # 한국어 번역 스크립트가 들어갔는지
        return c.get("/openapi.json").json()


def test_every_operation_has_korean_summary_and_description(spec):
    ops = [(p, m, o) for p, item in spec["paths"].items() for m, o in item.items()]
    assert len(ops) == 25
    for path, method, op in ops:
        assert HANGUL.search(op["summary"]), f"{method} {path}: 한국어 제목 없음"
        assert HANGUL.search(op["description"]), f"{method} {path}: 한국어 설명 없음"
        assert op["tags"] and all(HANGUL.search(t) for t in op["tags"])


def test_tags_and_app_description(spec):
    assert len(spec["tags"]) == 7 and all(HANGUL.search(t["description"]) for t in spec["tags"])
    assert HANGUL.search(spec["info"]["description"]) and "처음 써보는 순서" in spec["info"]["description"]


def test_request_bodies_have_examples_and_field_descriptions(spec):
    schemas = spec["components"]["schemas"]
    for name in ("SessionCreate", "AnswersIn", "CompleteIn", "SignupIn", "LoginIn", "AiSearchIn", "BacklogIn", "ScheduleIn"):
        assert schemas[name].get("examples"), f"{name}: 예시 없음"
        for field, prop in schemas[name]["properties"].items():
            assert HANGUL.search(prop.get("description", "")), f"{name}.{field}: 설명 없음"


def test_path_and_header_parameters_are_described(spec):
    for path in ("/api/sessions/{session_id}/answers", "/api/games/{game_id}", "/api/ai/deals"):
        for item in spec["paths"][path].values():
            for p in item.get("parameters", []):
                if p["in"] in ("path", "query"):
                    assert HANGUL.search(p.get("description", "")), f"{path} {p['name']}: 설명 없음"
    admin = spec["paths"]["/api/admin/games/sync"]["post"]
    assert any(p["name"] == "x-admin-token" and HANGUL.search(p.get("description", "")) for p in admin["parameters"])
