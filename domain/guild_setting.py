from dataclasses import dataclass
from typing import Optional


@dataclass
class GuildSetting:
    id: Optional[int]
    guild_id: int
    default_race: Optional[str]
    default_server: Optional[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
