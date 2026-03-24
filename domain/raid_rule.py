from dataclasses import dataclass, field
from typing import List


@dataclass
class RaidRule:
    guild_id: int
    channel_id: int
    raid_name: str

    party1_priority_jobs: List[str] = field(default_factory=list)
    party1_preferred_jobs: List[str] = field(default_factory=list)
    party2_priority_jobs: List[str] = field(default_factory=list)
    party2_preferred_jobs: List[str] = field(default_factory=list)

    @staticmethod
    def empty(guild_id: int, channel_id: int, raid_name: str) -> "RaidRule":
        return RaidRule(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name,
            party1_priority_jobs=[],
            party1_preferred_jobs=[],
            party2_priority_jobs=[],
            party2_preferred_jobs=[],
        )
