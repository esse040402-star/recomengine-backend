import asyncio
import json
import re

import httpx

from app.config import get_settings

_sem: asyncio.Semaphore | None = None


def _semaphore() -> asyncio.Semaphore:
    """로컬 PC가 과부하되지 않도록 Ollama 동시 요청 수를 제한한다."""
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(max(1, get_settings().ollama_concurrency))
    return _sem


async def list_models() -> list[str] | None:
    """설치된 모델 이름 목록. Ollama가 꺼져 있으면 None."""
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            r = await client.get(f"{get_settings().ollama_base_url}/api/tags")
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return None


def model_installed(configured: str, installed: list[str]) -> bool:
    """'llama3' 처럼 태그를 생략해도 'llama3:latest' 와 같은 모델로 본다."""
    return any(n == configured or (":" not in configured and n == f"{configured}:latest") for n in installed)


async def is_up() -> bool:
    return await list_models() is not None


async def model_ready() -> bool:
    models = await list_models()
    return models is not None and model_installed(get_settings().ollama_model, models)


def parse_json_object(text: str) -> dict:
    """모델이 JSON 앞뒤에 말을 붙이거나 코드펜스를 쳐도 첫 JSON 객체를 꺼낸다."""
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise ValueError("JSON 객체를 찾지 못했습니다.")
        data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON 객체가 아닙니다.")
    return data


async def chat_json(system: str, user: str, temperature: float = 0.4, max_tokens: int | None = None) -> dict:
    """Ollama /api/chat 을 JSON 모드로 호출해 dict로 돌려준다."""
    s = get_settings()
    options: dict = {"temperature": temperature}
    if max_tokens:
        options["num_predict"] = max_tokens
    payload = {
        "model": s.ollama_model,
        "stream": False,
        "format": "json",
        "keep_alive": s.ollama_keep_alive,  # 모델을 메모리에 잠시 유지해 다음 호출을 빠르게
        "options": options,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with _semaphore():
        async with httpx.AsyncClient(timeout=s.ollama_timeout) as client:
            r = await client.post(f"{s.ollama_base_url}/api/chat", json=payload)
            r.raise_for_status()
            content = r.json()["message"]["content"]
    return parse_json_object(content)
