from dataclasses import dataclass
from datetime import datetime


@dataclass
class LolApplication:
    id: int | None
    guild_id: int
    user_id: int
    user_name: str
    riot_id: str
    normalized_riot_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
