from dataclasses import dataclass


class PartyModifyError(Exception):
    pass


class ActivePartyBuildNotFoundError(PartyModifyError):
    pass


class WaitingMemberNotFoundError(PartyModifyError):
    pass


class PartySlotNotFoundError(PartyModifyError):
    pass


class PartyCapacityExceededError(PartyModifyError):
    pass


class DuplicateUserInGroupError(PartyModifyError):
    pass


@dataclass
class ModifyResult:
    message: str
    session_id: int


class PartyModifyService:
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

    def add_waiting_member_to_party(
        self,
        guild_id: int,
        channel_id: int,
        waiting_id: int,
        group_no: int,
        party_no: int,
    ):
        # 현재 세션 조회
        session = self.session_repository.get_active_session(
            guild_id, channel_id, self.raid_name
        )
    
        if session is None:
            raise Exception("공대가 없습니다.")
    
        # 🔥 현재 파티 인원 조회
        current_members = self.slot_repository.get_by_session_group_party(
            session.id,
            group_no,
            party_no,
        )
    
        # 🔥 핵심 체크 (정원 4명)
        if len(current_members) >= 4:
            raise Exception("해당 파티는 이미 가득 찼습니다.")
    
        # 상비군 조회
        waiting = self.waiting_repository.get_by_id(waiting_id)
        if waiting is None:
            raise Exception("상비군 정보를 찾을 수 없습니다.")
    
        # 슬롯 번호 자동 할당
        used_slots = [m["slot_no"] for m in current_members]
        for i in range(1, 5):
            if i not in used_slots:
                slot_no = i
                break
    
        # 슬롯 추가
        self.slot_repository.insert_slot(
            session_id=session.id,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=self.raid_name,
            group_no=group_no,
            party_no=party_no,
            slot_no=slot_no,
            application_id=waiting["application_id"],
            user_id=waiting["user_id"],
            user_name=waiting["user_name"],
            character_name=waiting["character_name"],
            job=waiting["job"],
            item_level=waiting["item_level"],
            combat_power=waiting["combat_power"],
        )
    
        # 상비군 삭제
        self.waiting_repository.delete_by_id(waiting_id)
    
        return f"{waiting['character_name']}을 {group_no}공대 {party_no}파티로 이동했습니다."

    def remove_party_member_to_waiting(
        self,
        guild_id: int,
        channel_id: int,
        slot_id: int,
    ) -> ModifyResult:
        session = self._get_active_session(guild_id, channel_id)

        slot = self.party_slot_repository.get_by_id(slot_id)
        if slot is None or slot["session_id"] != session.id:
            raise PartySlotNotFoundError("공대원을 찾을 수 없습니다.")

        self.party_waiting_repository.insert_waiting(
            session_id=session.id,
            guild_id=slot["guild_id"],
            channel_id=slot["channel_id"],
            raid_name=slot["raid_name"],
            application_id=slot["application_id"],
            user_id=slot["user_id"],
            user_name=slot["user_name"],
            character_name=slot["character_name"],
            job=slot["job"],
            item_level=slot["item_level"],
            combat_power=slot["combat_power"],
        )

        self.party_slot_repository.delete_by_id(slot_id)
        self.party_slot_repository.reorder_party_slots(
            session_id=session.id,
            group_no=slot["group_no"],
            party_no=slot["party_no"],
        )

        self.party_build_session_repository.update_waiting_count(
            session_id=session.id,
            waiting_count=self.party_waiting_repository.count_by_session_id(session.id),
        )

        return ModifyResult(
            message=(
                f"{slot['group_no']}공대 {slot['party_no']}파티의 "
                f"{slot['character_name']}을(를) 대기 인원으로 이동했습니다."
            ),
            session_id=session.id,
        )

    def swap_party_member_with_waiting(
        self,
        guild_id: int,
        channel_id: int,
        slot_id: int,
        waiting_id: int,
    ) -> ModifyResult:
        session = self._get_active_session(guild_id, channel_id)

        slot = self.party_slot_repository.get_by_id(slot_id)
        if slot is None or slot["session_id"] != session.id:
            raise PartySlotNotFoundError("교체할 공대원을 찾을 수 없습니다.")

        waiting = self.party_waiting_repository.get_by_id(waiting_id)
        if waiting is None or waiting["session_id"] != session.id:
            raise WaitingMemberNotFoundError("교체할 대기 인원을 찾을 수 없습니다.")

        if waiting["user_id"] != slot["user_id"]:
            if self._has_same_user_in_group(
                session_id=session.id,
                group_no=slot["group_no"],
                user_id=waiting["user_id"],
                exclude_slot_id=slot_id,
            ):
                raise DuplicateUserInGroupError("교체 후 같은 공대에 동일한 유저 ID가 존재하게 됩니다.")

        # 기존 슬롯 공대원을 대기로 이동
        self.party_waiting_repository.insert_waiting(
            session_id=session.id,
            guild_id=slot["guild_id"],
            channel_id=slot["channel_id"],
            raid_name=slot["raid_name"],
            application_id=slot["application_id"],
            user_id=slot["user_id"],
            user_name=slot["user_name"],
            character_name=slot["character_name"],
            job=slot["job"],
            item_level=slot["item_level"],
            combat_power=slot["combat_power"],
        )

        # 슬롯은 대기 인원 정보로 교체
        self.party_slot_repository.update_slot_member(
            slot_id=slot_id,
            application_id=waiting["application_id"],
            user_id=waiting["user_id"],
            user_name=waiting["user_name"],
            character_name=waiting["character_name"],
            job=waiting["job"],
            item_level=waiting["item_level"],
            combat_power=waiting["combat_power"],
        )

        self.party_waiting_repository.delete_by_id(waiting_id)

        self.party_build_session_repository.update_waiting_count(
            session_id=session.id,
            waiting_count=self.party_waiting_repository.count_by_session_id(session.id),
        )

        return ModifyResult(
            message=(
                f"대기 인원 {waiting['character_name']}과(와) "
                f"{slot['group_no']}공대 {slot['party_no']}파티의 "
                f"{slot['character_name']}을(를) 교체했습니다."
            ),
            session_id=session.id,
        )

    def _get_active_session(self, guild_id: int, channel_id: int):
        raid = self.raid_service.get_channel_raid(channel_id)
        if raid is None:
            raise ActivePartyBuildNotFoundError("설정된 레이드가 없습니다.")

        session = self.party_build_session_repository.get_active_session(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )
        if session is None:
            raise ActivePartyBuildNotFoundError("현재 생성된 공대 결과가 없습니다.")

        return session

    def _has_same_user_in_group(
        self,
        session_id: int,
        group_no: int,
        user_id: int,
        exclude_slot_id: int | None = None,
    ) -> bool:
        slots = self.party_slot_repository.get_by_session_id(session_id)

        for slot in slots:
            if slot["group_no"] != group_no:
                continue
            if exclude_slot_id is not None and slot["id"] == exclude_slot_id:
                continue
            if slot["user_id"] == user_id:
                return True

        return False

    def _is_temp_group_in_session(
        self,
        session_id: int,
        group_no: int,
    ) -> bool:
        slots = self.party_slot_repository.get_by_session_id(session_id)
        for slot in slots:
            if slot["group_no"] == group_no:
                return slot["is_temp_group"]
        return False
