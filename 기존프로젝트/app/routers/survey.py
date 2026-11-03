import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app import docs
from app.schemas import SurveyGenerateIn
from app.services import ollama, survey_ai

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/survey", tags=[docs.SURVEY])


@router.post("/generate", **docs.doc("survey_generate"))
async def generate(body: SurveyGenerateIn):
    """프론트의 심화 설문(28문항)을 Ollama로 자연스럽게 다시 써서 돌려준다.
    프론트는 body.blueprint 에 E.publicBlueprint(track, answers) 결과를 함께 보내야 한다
    (React 프론트의 frontend/src/services/recommendationService.js 가 이미 보낸다)."""
    if not body.blueprint:
        raise HTTPException(422, "blueprint가 필요합니다. 프론트에서 E.publicBlueprint() 결과를 함께 보내세요.")
    if len(body.blueprint) != 28:
        raise HTTPException(422, "blueprint는 28문항이어야 합니다.")

    blueprint = [q.model_dump() for q in body.blueprint]
    axes = body.profileContext.axes if body.profileContext else None
    prompt = survey_ai.build_prompt(body.track, blueprint, body.request, axes)
    try:
        # 프론트 타임아웃(55초)보다 먼저 끝내서 프론트가 안전하게 기본 문항으로 넘어가게 한다
        payload = await asyncio.wait_for(ollama.chat_json(survey_ai.SYSTEM, prompt, temperature=0.6), timeout=50)
    except Exception as exc:
        log.warning("설문 생성 실패: %s", exc)
        raise HTTPException(503, "AI 서버에서 설문을 만들지 못했습니다.")

    questions, rewritten = survey_ai.sanitize(blueprint, payload)
    if rewritten == 0:
        raise HTTPException(502, "AI 응답이 형식에 맞지 않았습니다.")
    return {"questions": questions, "source": "ollama", "rewritten": rewritten}
