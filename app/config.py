from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # true 이면 Supabase 없이 메모리 내 가짜 DB로 동작 (app/mock_db.py)
    use_mock_db: bool = False
    supabase_url: str = ""
    supabase_service_key: str = ""
    # 로그인 검증 전용(anon 키는 공개되어도 되는 키). 서비스 키로 로그인하면 안 되기 때문에 별도로 필요
    supabase_anon_key: str = ""

    # 로그인 세션 쿠키 서명용 비밀키 (python -c "import secrets;print(secrets.token_urlsafe(32))")
    session_secret: str = ""
    session_days: int = 30
    cookie_secure: bool = False  # HTTPS로 배포하면 true

    rawg_api_key: str = ""
    igdb_client_id: str = ""
    igdb_client_secret: str = ""

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout: float = 120.0
    ollama_keep_alive: str = "10m"
    ollama_concurrency: int = 2

    # (선택) 스팀 라이브러리 연동용. https://steamcommunity.com/dev/apikey
    steam_api_key: str = ""

    admin_token: str = ""
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    @model_validator(mode="after")
    def _require_supabase_unless_mock(self):
        if not self.use_mock_db and not (self.supabase_url and self.supabase_service_key):
            raise ValueError(
                "SUPABASE_URL / SUPABASE_SERVICE_KEY 가 필요합니다. "
                "DB 없이 테스트하려면 .env 에 USE_MOCK_DB=true 를 설정하세요."
            )
        return self

    @model_validator(mode="after")
    def _check_session_secret(self):
        if self.session_secret and len(self.session_secret) < 16:
            raise ValueError("SESSION_SECRET 은 16자 이상이어야 합니다.")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def rawg_enabled(self) -> bool:
        return bool(self.rawg_api_key)

    @property
    def igdb_enabled(self) -> bool:
        return bool(self.igdb_client_id and self.igdb_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
