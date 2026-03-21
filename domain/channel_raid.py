from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ChannelRaid:
    id: Optional[int]
    guild_id: int
    channel_id: int
    raid_name: str
    min_item_level: Optional[int]
    min_combat_power: Optional[int]
    entry_condition_text: Optional[str]
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
