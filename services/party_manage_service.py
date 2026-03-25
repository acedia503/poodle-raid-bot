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


class PartyManageService:
    def __init__(
        self,
        raid_service,
        party_build_session_repository,
        party_slot_repository,
        party_waiting_repository,
    ):
        self.raid_service = raid_service
        self.party_build_session_repository = party_build_session_repository
        self.party_slot_repository = party_slot_repository
        self.party_waiting_repository = party_waiting_repository

    def get_active_build_result(
        self,
        guild_id: int,
        channel_id: int,
    ) -> ActivePartyBuildView | None:
        raid = self.raid_service.get_channel_raid(channel_id)
        if raid is None:
            return None

        session = self.party_build_session_repository.get_active_session(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )
        if session is None:
            return None

        slot_rows = self.party_slot_repository.get_by_session_id(session.id)
        waiting_rows = self.party_waiting_repository.get_by_session_id(session.id)

        parties_map: dict[tuple[int, int], PartyViewData] = {}

        for row in slot_rows:
            key = (row["group_no"], row["party_no"])
            if key not in parties_map:
                parties_map[key] = PartyViewData(
                    group_no=row["group_no"],
                    party_no=row["party_no"],
                    is_temp_group=row["is_temp_group"],
                    total_combat_power=0,
                    members=[],
                )

            member = PartyMemberView(
                slot_no=row["slot_no"],
                user_id=row["user_id"],
                user_name=row["user_name"],
                character_name=row["character_name"],
                job=row["job"],
                item_level=row["item_level"],
                combat_power=row["combat_power"],
            )
            parties_map[key].members.append(member)
            parties_map[key].total_combat_power += row["combat_power"]

        parties = list(parties_map.values())
        parties.sort(key=lambda p: (p.group_no, p.party_no))
        for party in parties:
            party.members.sort(key=lambda m: m.slot_no)

        waiting_members = [
            WaitingMemberView(
                user_id=row["user_id"],
                user_name=row["user_name"],
                character_name=row["character_name"],
                job=row["job"],
                item_level=row["item_level"],
                combat_power=row["combat_power"],
            )
            for row in waiting_rows
        ]

        return ActivePartyBuildView(
            session_id=session.id,
            raid_name=session.raid_name,
            total_applicants=session.total_applicants,
            full_group_count=session.full_group_count,
            temp_group_count=session.temp_group_count,
            waiting_count=session.waiting_count,
            parties=parties,
            waiting_members=waiting_members,
        )

    def reset_active_build_result(
        self,
        guild_id: int,
        channel_id: int,
    ) -> bool:
        raid = self.raid_service.get_channel_raid(channel_id)
        if raid is None:
            return False

        session = self.party_build_session_repository.get_active_session(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )
        if session is None:
            return False

        self.party_build_session_repository.deactivate_existing_sessions(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )
        return True
