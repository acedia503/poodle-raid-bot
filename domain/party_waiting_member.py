from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.enums import WaitingStatus


@dataclass
class PartyWaitingMember:
    id: Optional[int]
    session_id: int
    application_id: int
    waiting_status: WaitingStatus
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
