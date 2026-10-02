import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import docs
from app.config import get_settings
from app.routers import account, ai, games, sessions, survey, system

logging.basicConfig(level=logging.INFO)
# httpx 는 요청 주소 전체를 INFO 로그로 남기는데, RAWG·스팀은 API 키를 주소(?key=...)에 넣어서
# 터미널에 키가 그대로 찍힌다. 경고 이상만 남긴다.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

app = FastAPI(
    title="RecomEngine API (게임 추천 백엔드)",
    description=docs.APP_DESCRIPTION,
    version="0.1.0",
    openapi_tags=docs.OPENAPI_TAGS,
    docs_url=None,  # 기본 /docs 대신 아래에서 한국어 설명을 붙인 /docs 를 직접 만든다
    # 각 항목을 펼치면 'Try it out' 이 이미 눌려 있고, 응답 시간도 보여준다
    swagger_ui_parameters={"tryItOutEnabled": True, "displayRequestDuration": True, "docExpansion": "list"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST", "PUT"],
    allow_credentials=True,  # 다른 주소의 프론트에서 쿠키 로그인을 쓸 때 필요 (CORS_ORIGINS 에 정확한 주소를 넣어야 함)
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
)


# Swagger UI의 영어 고정 문구(Parameters, Execute, Responses …) 옆에 한국어를 붙이는 스크립트
SWAGGER_KO_JS = (Path(__file__).resolve().parent / "static" / "swagger_ko.js").read_text(encoding="utf-8")


@app.get("/docs", include_in_schema=False)
async def swagger_ui_korean() -> HTMLResponse:
    page = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API 문서",
        swagger_ui_parameters=app.swagger_ui_parameters,
    )
    html = page.body.decode("utf-8")
    script = f"<script>{SWAGGER_KO_JS}</script>"
    html = html.replace("</body>", script + "</body>", 1) if "</body>" in html else html + script
    return HTMLResponse(html)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    """프론트는 실패 응답의 {"error": "..."} 를 그대로 사용자에게 보여준다 (FastAPI 기본은 {"detail": ...})."""
    message = exc.detail if isinstance(exc.detail, str) else "요청을 처리하지 못했어요."
    return JSONResponse({"error": message, "detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    # pydantic 오류의 input 에는 사용자가 보낸 값(비밀번호 등)이 들어 있어서 응답에서 뺀다
    safe = [{k: v for k, v in e.items() if k not in ("input", "ctx", "url")} for e in exc.errors()]
    return JSONResponse({"error": "입력한 내용을 다시 확인해 주세요.", "detail": jsonable_encoder(safe)}, status_code=422)


app.include_router(system.router)
app.include_router(account.router)
app.include_router(games.router)
app.include_router(survey.router)
app.include_router(sessions.router)
app.include_router(ai.router)

# 프로토타입 HTML은 /api/... 상대경로를 쓰므로 같은 서버에서 서빙하는 게 가장 간단하다.
# backend/frontend/index.html 로 넣어두면 http://localhost:8000/ 에서 열린다.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if (FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
