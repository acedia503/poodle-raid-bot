import os
from dataclasses import dataclass


@dataclass
class Config:
    discord_token: str
    api_base_url: str
    api_timeout: int
    db_url: str


def load_config() -> Config:
    return Config(
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        db_path=os.getenv("DB_PATH", "bot.db"),
        api_base_url=os.getenv("API_BASE_URL", ""),
        api_timeout=int(os.getenv("API_TIMEOUT", "10")),
    )
