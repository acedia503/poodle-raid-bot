from domain.enums import ApplicationStatus, WaitingStatus
from domain.party_slot import PartySlot
from domain.party_waiting_member import PartyWaitingMember
from repositories.party_build_session_repository import PartyBuildSessionRepository
from repositories.party_slot_repository import PartySlotRepository
from repositories.party_waiting_repository import PartyWaitingRepository
from repositories.raid_application_repository import RaidApplicationRepository


class PartyManageService:
    def __init__(
        self,
        session_repository: PartyBuildSessionRepository,
        slot_repository: PartySlotRepository,
        waiting_repository: PartyWaitingRepository,
        raid_application_repository: RaidApplicationRepository,
    ):
        self.session_repository = session_repository
        self.slot_repository = slot_repository
        self.waiting_repository = waiting_repository
        self.raid_application_repository = raid_application_repository

    def get_latest_session(self, guild_id: int, channel_id: int, raid_name: str):
        return self.session_repository.get_latest_by_channel_and_raid(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name,
        )

    def validate_slot_empty(
        self,
        session_id: int,
        group_no: int,
        party_no: int,
        slot_no: int,
    ) -> bool:
        target = self.slot_repository.get_by_position(session_id, group_no, party_no, slot_no)
        return target is None

    def move_member(
        self,
        session_id: int,
        from_slot_id: int,
        to_group_no: int,
        to_party_no: int,
        to_slot_no: int,
    ) -> bool:
        if not self.validate_slot_empty(session_id, to_group_no, to_party_no, to_slot_no):
            raise ValueError("도착 슬롯이 비어 있지 않습니다.")

        return self.slot_repository.update_slot(
            from_slot_id,
            group_no=to_group_no,
            party_no=to_party_no,
            slot_no=to_slot_no,
        )

    def swap_members(self, session_id: int, slot_id_a: int, slot_id_b: int) -> bool:
        slot_a = self.slot_repository.get_by_id(slot_id_a)
        slot_b = self.slot_repository.get_by_id(slot_id_b)

        if slot_a is None or slot_b is None:
            raise ValueError("교체 대상 슬롯을 찾을 수 없습니다.")

        pos_a = (slot_a.group_no, slot_a.party_no, slot_a.slot_no)
        pos_b = (slot_b.group_no, slot_b.party_no, slot_b.slot_no)

        ok1 = self.slot_repository.update_slot(
            slot_id_a,
            group_no=pos_b[0],
            party_no=pos_b[1],
            slot_no=pos_b[2],
        )
        ok2 = self.slot_repository.update_slot(
            slot_id_b,
            group_no=pos_a[0],
            party_no=pos_a[1],
            slot_no=pos_a[2],
        )
        return ok1 and ok2

    def move_to_waiting(self, session_id: int, slot_id: int) -> bool:
        slot = self.slot_repository.get_by_id(slot_id)
        if slot is None or slot.application_id is None:
            return False

        self.waiting_repository.create(
            PartyWaitingMember(
                id=None,
                session_id=session_id,
                application_id=slot.application_id,
                waiting_status=WaitingStatus.WAITING,
            )
        )
        self.raid_application_repository.update_status(
            slot.application_id,
            ApplicationStatus.WAITING.value,
        )
        return self.slot_repository.delete_by_id(slot_id)

    def exclude_member_from_slot(self, session_id: int, slot_id: int) -> bool:
        slot = self.slot_repository.get_by_id(slot_id)
        if slot is None or slot.application_id is None:
            return False

        self.waiting_repository.create(
            PartyWaitingMember(
                id=None,
                session_id=session_id,
                application_id=slot.application_id,
                waiting_status=WaitingStatus.EXCLUDED,
            )
        )
        self.raid_application_repository.update_status(
            slot.application_id,
            ApplicationStatus.EXCLUDED.value,
        )
        return self.slot_repository.delete_by_id(slot_id)

    def restore_from_waiting(
        self,
        session_id: int,
        waiting_id: int,
        to_group_no: int,
        to_party_no: int,
        to_slot_no: int,
    ) -> bool:
        if not self.validate_slot_empty(session_id, to_group_no, to_party_no, to_slot_no):
            raise ValueError("도착 슬롯이 비어 있지 않습니다.")

        waiting = self.waiting_repository.get_by_id(waiting_id)
        if waiting is None:
            return False

        applications = self.raid_application_repository.get_by_ids([waiting.application_id])
        if not applications:
            return False
        app = applications[0]

        self.slot_repository.bulk_create([
            PartySlot(
                id=None,
                session_id=session_id,
                guild_id=app.guild_id,
                raid_name=app.raid_name,
                group_no=to_group_no,
                party_no=to_party_no,
                slot_no=to_slot_no,
                application_id=app.id,
                user_id=app.user_id,
                character_name=app.character_name,
                job=app.job,
                item_level=app.item_level,
                combat_power=app.combat_power,
            )
        ])
        self.raid_application_repository.update_status(app.id, ApplicationStatus.ASSIGNED.value)
        return self.waiting_repository.delete_by_id(waiting_id)

    def exclude_member_from_waiting(self, session_id: int, waiting_id: int) -> bool:
        waiting = self.waiting_repository.get_by_id(waiting_id)
        if waiting is None:
            return False

        self.raid_application_repository.update_status(
            waiting.application_id,
            ApplicationStatus.EXCLUDED.value,
        )
        return True

    def reset_latest_party(self, guild_id: int, channel_id: int, raid_name: str) -> bool:
        session = self.session_repository.get_latest_by_channel_and_raid(guild_id, channel_id, raid_name)
        if session is None:
            return False

        slots = self.slot_repository.get_by_session_id(session.id)
        waiting = self.waiting_repository.get_by_session_id(session.id)

        application_ids = []
        application_ids.extend([slot.application_id for slot in slots if slot.application_id is not None])
        application_ids.extend([member.application_id for member in waiting])

        if application_ids:
            self.raid_application_repository.bulk_update_status(
                application_ids,
                ApplicationStatus.APPLIED.value,
            )

        return self.session_repository.delete_by_id(session.id)
