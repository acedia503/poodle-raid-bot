import os
from dataclasses import dataclass


@dataclass
class Config:
    discord_token: str
    db_path: str
    api_mode: str
    api_base_url: str
    api_timeout: int
    api_key: str | None
    api_character_path: str
    api_auth_header_name: str | None


def load_config() -> Config:
    return Config(
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        db_path=os.getenv("DB_PATH", "bot.db"),
        api_mode=os.getenv("API_MODE", "mock"),  # mock | http
        api_base_url=os.getenv("API_BASE_URL", ""),
        api_timeout=int(os.getenv("API_TIMEOUT", "5")),
        api_key=os.getenv("API_KEY"),
        api_character_path=os.getenv("API_CHARACTER_PATH", "/characters"),
        api_auth_header_name=os.getenv("API_AUTH_HEADER_NAME", "Authorization"),
    )
