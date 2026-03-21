from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.enums import ApplicationStatus, SourceType


@dataclass
class RaidApplication:
    id: Optional[int]
    guild_id: int
    channel_id: int
    raid_name: str
    user_id: int
    user_name: str
    character_name: str
    job: str
    item_level: int
    combat_power: int
    application_status: ApplicationStatus
    source_type: SourceType
    created_by_user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
