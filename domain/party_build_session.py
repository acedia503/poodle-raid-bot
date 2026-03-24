from dataclasses import dataclass


@dataclass
class PartyBuildSession:
    id: int | None
    guild_id: int
    channel_id: int
    raid_name: str
    total_applicants: int
    full_group_count: int
    temp_group_count: int
    waiting_count: int
    created_by: int
    is_active: bool = True
