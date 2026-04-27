from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RaidApplication:
    id: int | None
    guild_id: int
    channel_id: int
    user_id: int
    user_name: str
    character_name: str
    race: str
    server: str
    job: str
    item_level: int
    combat_power: int
    raid_name: str
    character_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
