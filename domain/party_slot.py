from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PartySlot:
    id: Optional[int]
    session_id: int
    guild_id: int
    raid_name: str
    group_no: int
    party_no: int
    slot_no: int
    application_id: Optional[int]
    user_id: Optional[int]
    character_name: Optional[str]
    job: Optional[str]
    item_level: Optional[int]
    combat_power: Optional[int]
    slot_status: str = "assigned"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
