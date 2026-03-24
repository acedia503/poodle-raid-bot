from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.enums import BalanceMode


@dataclass
class RaidRule:
    def __init__(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
        party1_priority_jobs: list[str] | None = None,
        party1_preferred_jobs: list[str] | None = None,
        party2_priority_jobs: list[str] | None = None,
        party2_preferred_jobs: list[str] | None = None,
    ):
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.raid_name = raid_name
        self.party1_priority_jobs = party1_priority_jobs or []
        self.party1_preferred_jobs = party1_preferred_jobs or []
        self.party2_priority_jobs = party2_priority_jobs or []
        self.party2_preferred_jobs = party2_preferred_jobs or []
