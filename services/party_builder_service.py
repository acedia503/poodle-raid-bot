from collections import defaultdict

from domain.enums import ApplicationStatus, SessionStatus, WaitingStatus
from domain.party_build_session import PartyBuildSession
from domain.party_slot import PartySlot
from domain.party_waiting_member import PartyWaitingMember
from domain.raid_application import RaidApplication
from repositories.party_build_session_repository import PartyBuildSessionRepository
from repositories.party_slot_repository import PartySlotRepository
from repositories.party_waiting_repository import PartyWaitingRepository
from repositories.raid_application_repository import RaidApplicationRepository
from services.party_rule_service import PartyRuleService
from services.raid_service import RaidService


class PartyBuilderService:
    def __init__(
        self,
        raid_service: RaidService,
        party_rule_service: PartyRuleService,
        raid_application_repository: RaidApplicationRepository,
        session_repository: PartyBuildSessionRepository,
        slot_repository: PartySlotRepository,
        waiting_repository: PartyWaitingRepository,
    ):
        self.raid_service = raid_service
        self.party_rule_service = party_rule_service
        self.raid_application_repository = raid_application_repository
        self.session_repository = session_repository
        self.slot_repository = slot_repository
        self.waiting_repository = waiting_repository

    def build_party(
        self,
        guild_id: int,
        channel_id: int,
        created_by_user_id: int,
    ) -> PartyBuildSession:
        channel_raid = self.raid_service.get_channel_raid(channel_id)
        if channel_raid is None:
            raise ValueError("현재 채널에 연결된 레이드가 없습니다.")

        applications = self.load_target_applications(guild_id, channel_raid.raid_name)
        if not applications:
            raise ValueError("신청자가 없습니다.")

        rule = self.party_rule_service.get_or_create_default_rule(
            guild_id=guild_id,
            raid_name=channel_raid.raid_name,
        )

        session = self.session_repository.create(
            PartyBuildSession(
                id=None,
                guild_id=guild_id,
                channel_id=channel_id,
                raid_name=channel_raid.raid_name,
                session_status=SessionStatus.FINALIZED,
                created_by_user_id=created_by_user_id,
            )
        )

        slots, waiting = self.run_balance_algorithm(
            session_id=session.id,
            guild_id=guild_id,
            raid_name=channel_raid.raid_name,
            applications=applications,
            group_size=rule.group_size,
            party_count=rule.party_count,
            slots_per_party=rule.slots_per_party,
        )

        self.slot_repository.bulk_create(slots)
        self.waiting_repository.bulk_create(waiting)

        assigned_ids = [slot.application_id for slot in slots if slot.application_id is not None]
        waiting_ids = [member.application_id for member in waiting if member.waiting_status == WaitingStatus.WAITING]
        excluded_ids = [member.application_id for member in waiting if member.waiting_status == WaitingStatus.EXCLUDED]

        if assigned_ids:
            self.raid_application_repository.bulk_update_status(
                assigned_ids,
                ApplicationStatus.ASSIGNED.value,
            )
        if waiting_ids:
            self.raid_application_repository.bulk_update_status(
                waiting_ids,
                ApplicationStatus.WAITING.value,
            )
        if excluded_ids:
            self.raid_application_repository.bulk_update_status(
                excluded_ids,
                ApplicationStatus.EXCLUDED.value,
            )

        return session

    def load_target_applications(self, guild_id: int, raid_name: str) -> list[RaidApplication]:
        return self.raid_application_repository.get_applications_by_raid(
            guild_id=guild_id,
            raid_name=raid_name,
            statuses=[ApplicationStatus.APPLIED.value],
        )

    def run_balance_algorithm(
        self,
        session_id: int,
        guild_id: int,
        raid_name: str,
        applications: list[RaidApplication],
        group_size: int,
        party_count: int,
        slots_per_party: int,
    ) -> tuple[list[PartySlot], list[PartyWaitingMember]]:
        applications = sorted(
            applications,
            key=lambda x: (x.combat_power, x.item_level),
            reverse=True,
        )

        total_capacity = ((len(applications) + group_size - 1) // group_size) * group_size
        assign_count = min(len(applications), total_capacity)

        assigned_apps = applications[:assign_count]
        waiting_apps = applications[assign_count:]

        groups: defaultdict[int, list[RaidApplication]] = defaultdict(list)
        current_group_no = 1

        for app in assigned_apps:
            groups[current_group_no].append(app)
            if len(groups[current_group_no]) >= group_size:
                current_group_no += 1

        slots: list[PartySlot] = []
        for group_no, members in groups.items():
            for idx, app in enumerate(members):
                party_no = (idx // slots_per_party) + 1
                slot_no = (idx % slots_per_party) + 1

                slots.append(
                    PartySlot(
                        id=None,
                        session_id=session_id,
                        guild_id=guild_id,
                        raid_name=raid_name,
                        group_no=group_no,
                        party_no=party_no,
                        slot_no=slot_no,
                        application_id=app.id,
                        user_id=app.user_id,
                        character_name=app.character_name,
                        job=app.job,
                        item_level=app.item_level,
                        combat_power=app.combat_power,
                    )
                )

        waiting_members = [
            PartyWaitingMember(
                id=None,
                session_id=session_id,
                application_id=app.id,
                waiting_status=WaitingStatus.WAITING,
                sort_order=index,
            )
            for index, app in enumerate(waiting_apps, start=1)
        ]

        return slots, waiting_members
