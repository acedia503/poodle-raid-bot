from dataclasses import dataclass


@dataclass
class PartySlot:
    id: int | None
    session_id: int
    guild_id: int
    channel_id: int
    raid_name: str
    group_no: int
    party_no: int
    slot_no: int
    is_temp_group: bool
    application_id: int
    user_id: int
    user_name: str
    character_name: str
    job: str
    item_level: int
    combat_power: int
