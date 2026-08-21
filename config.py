import os
from dataclasses import dataclass


@dataclass
class Config:
    discord_token: str
    database_url: str
    api_mode: str
    api_base_url: str
    api_timeout: int
    api_key: str | None
    api_character_path: str
    api_auth_header_name: str | None
    db_pool_min_size: int
    db_pool_max_size: int


def load_config() -> Config:
    return Config(
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", ""),
        api_mode=os.getenv("API_MODE", "http"),
        api_base_url=os.getenv("API_BASE_URL", ""),
        api_timeout=int(os.getenv("API_TIMEOUT", "5")),
        api_key=os.getenv("API_KEY"),
        api_character_path=os.getenv("API_CHARACTER_PATH", "/characters"),
        api_auth_header_name=os.getenv("API_AUTH_HEADER_NAME", "Authorization"),
        db_pool_min_size=int(os.getenv("DB_POOL_MIN_SIZE", "1")),
        db_pool_max_size=int(os.getenv("DB_POOL_MAX_SIZE", "15")),
    )
