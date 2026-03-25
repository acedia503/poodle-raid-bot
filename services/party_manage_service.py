from dataclasses import dataclass, field


@dataclass
class PartyMemberView:
    slot_no: int
    user_id: int
    user_name: str
    character_name: str
    job: str
    item_level: int
    combat_power: int


@dataclass
class PartyViewData:
    group_no: int
    party_no: int
    is_temp_group: bool
    total_combat_power: int
    members: list[PartyMemberView] = field(default_factory=list)


@dataclass
class WaitingMemberView:
    user_id: int
    user_name: str
    character_name: str
    job: str
    item_level: int
    combat_power: int


@dataclass
class ActivePartyBuildView:
    session_id: int
    raid_name: str
    total_applicants: int
    full_group_count: int
    temp_group_count: int
    waiting_count: int
    parties: list[PartyViewData]
    waiting_members: list[WaitingMemberView]
