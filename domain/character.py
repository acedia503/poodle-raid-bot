from dataclasses import dataclass
from datetime import datetime


@dataclass
class Character:
    id: int | None
    guild_id: int
    user_id: int
    user_name: str
    character_name: str
    race: str
    server: str
    job: str
    item_level: int
    combat_power: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
