from functools import lru_cache
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    project_root = backend_dir.parent
    for env_path in (project_root / ".env", backend_dir / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


load_environment()


class Settings:
    amap_web_service_key: str = getenv("AMAP_WEB_SERVICE_KEY", "")
    llm_api_key: str = getenv("LLM_API_KEY", "")
    llm_base_url: str = getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = getenv("LLM_MODEL", "gpt-4o-mini")
    frontend_origin: str = getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    research_mode: str = getenv("RESEARCH_MODE", "llm_grounding")
    llm_grounding_provider: str = getenv("LLM_GROUNDING_PROVIDER", "gemini")
    gemini_api_key: str = getenv("GEMINI_API_KEY", "")
    gemini_grounding_model: str = getenv("GEMINI_GROUNDING_MODEL", "gemini-2.5-pro")
    dashscope_api_key: str = getenv("DASHSCOPE_API_KEY", "")
    dashscope_web_search_agent_id: str = getenv("DASHSCOPE_WEB_SEARCH_AGENT_ID", "")
    dashscope_web_search_agent_version: str = getenv("DASHSCOPE_WEB_SEARCH_AGENT_VERSION", "beta")
    dashscope_web_search_api_url: str = getenv(
        "DASHSCOPE_WEB_SEARCH_API_URL",
        "https://dashscope.aliyuncs.com/api/v2/apps/web-search-agent/chat/completions",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
