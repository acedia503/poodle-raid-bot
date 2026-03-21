from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.enums import BalanceMode


@dataclass
class RaidRule:
    id: Optional[int]
    guild_id: int
    raid_name: str
    group_size: int
    party_count: int
    slots_per_party: int
    balance_mode: BalanceMode
    rule_data_json: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
