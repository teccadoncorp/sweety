from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://sweety:sweety@db:5432/sweety"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    app_name: str = "Sweety"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "openai/gpt-4o-mini"
    sweety_chat_model: str = ""
    sweety_image_model: str = "google/gemini-2.5-flash-image"
    sweety_search_model: str = "openai/gpt-4o-mini"
    sweety_public_url: str = "http://localhost:3000"
    sweety_api_public_url: str = "http://localhost:3000"
    cors_origins: str = ""
    seed_demo: bool = True
    seed_email: str = "board@sweety.local"
    seed_password: str = "sweety"
    heartbeat_scan_seconds: int = 60
    agent_max_tool_rounds: int = 12
    checkout_lease_minutes: int = 30
    media_dir: str = "/app/data/media"
    require_publish_approval: bool = True

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    facebook_client_id: str = ""
    facebook_client_secret: str = ""

    heygen_api_key: str = ""
    heygen_default_avatar_id: str = ""
    heygen_default_voice_id: str = ""
    tavily_api_key: str = ""
    brave_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cors_origin_list() -> list[str]:
    s = get_settings()
    origins = [
        s.sweety_public_url.rstrip("/"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://34.255.116.239",
    ]
    origins.extend(part.strip().rstrip("/") for part in s.cors_origins.split(",") if part.strip())
    return list(dict.fromkeys(origins))


def model_map() -> dict[str, str]:
    s = get_settings()
    return {
        "chat": s.sweety_chat_model or s.openrouter_default_model,
        "search": s.sweety_search_model or s.openrouter_default_model,
        "image": s.sweety_image_model,
        "video": "heygen",
    }
