from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GuildSetting:
    id: Optional[int]
    guild_id: int
    default_race: Optional[str]
    default_server: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
