from fastapi import APIRouter

from app import docs
from app.config import get_settings
from app.services import ollama

router = APIRouter(prefix="/api", tags=[docs.SYSTEM])


@router.get("/status", **docs.doc("status"))
async def status():
    s = get_settings()
    models = await ollama.list_models()
    ready = models is not None and ollama.model_installed(s.ollama_model, models)
    return {
        "ai": ready,  # 프론트: 심화 설문 AI 생성 사용 여부 (Ollama가 켜져 있고 모델이 설치됨)
        "feeds": False,  # 프론트: Steam 랭킹/뉴스/리뷰 라이브 API (아직 미구현)
        "ollama": {"up": models is not None, "model": s.ollama_model, "model_ready": ready},
        "rawg": s.rawg_enabled,
        "igdb": s.igdb_enabled,
        "steam": bool(s.steam_api_key),
        "mock_db": s.use_mock_db,
    }
