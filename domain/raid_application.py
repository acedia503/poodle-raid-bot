from dataclasses import dataclass
from typing import Optional


@dataclass
class RaidApplication:
    id: Optional[int]
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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
