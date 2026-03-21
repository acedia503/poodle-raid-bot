from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.enums import SessionStatus


@dataclass
class PartyBuildSession:
    id: Optional[int]
    guild_id: int
    channel_id: int
    raid_name: str
    session_status: SessionStatus
    created_by_user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
