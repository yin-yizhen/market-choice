from functools import lru_cache
from os import getenv


class Settings:
    amap_web_service_key: str = getenv("AMAP_WEB_SERVICE_KEY", "")
    llm_api_key: str = getenv("LLM_API_KEY", "")
    llm_base_url: str = getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = getenv("LLM_MODEL", "gpt-4o-mini")
    frontend_origin: str = getenv("FRONTEND_ORIGIN", "http://localhost:5173")


@lru_cache
def get_settings() -> Settings:
    return Settings()
