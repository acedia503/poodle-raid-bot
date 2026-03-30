# services/party_modify_service.py

from domain.party_slot import PartySlot


class PartyModifyService:
    def __init__(
        self,
        session_repository,
        slot_repository,
        waiting_repository,
    ):
        self.session_repository = session_repository
        self.slot_repository = slot_repository
        self.waiting_repository = waiting_repository

    def _get_active_session(self, guild_id, channel_id, raid_name):
        session = self.session_repository.get_active_session(
            guild_id,
            channel_id,
            raid_name,
        )
        if not session:
            raise Exception("활성 공대가 없습니다.")
        return session

    def remove_party_member_to_waiting(
        self,
        guild_id,
        channel_id,
        raid_name,
        slot_id,
    ):
        session = self._get_active_session(guild_id, channel_id, raid_name)

        slot = self.slot_repository.get_by_id(slot_id)
        if not slot:
            raise Exception("대상 공대원이 없습니다.")

        self.waiting_repository.insert_waiting(
            session_id=session.id,
            guild_id=slot["guild_id"] if isinstance(slot, dict) else slot.guild_id,
            channel_id=slot["channel_id"] if isinstance(slot, dict) else slot.channel_id,
            raid_name=slot["raid_name"] if isinstance(slot, dict) else slot.raid_name,
            application_id=slot["application_id"] if isinstance(slot, dict) else slot.application_id,
            user_id=slot["user_id"] if isinstance(slot, dict) else slot.user_id,
            user_name=slot["user_name"] if isinstance(slot, dict) else slot.user_name,
            character_name=slot["character_name"] if isinstance(slot, dict) else slot.character_name,
            job=slot["job"] if isinstance(slot, dict) else slot.job,
            item_level=slot["item_level"] if isinstance(slot, dict) else slot.item_level,
            combat_power=slot["combat_power"] if isinstance(slot, dict) else slot.combat_power,
        )

        self.slot_repository.delete_by_id(slot_id)

        group_no = slot["group_no"] if isinstance(slot, dict) else slot.group_no
        party_no = slot["party_no"] if isinstance(slot, dict) else slot.party_no
        character_name = slot["character_name"] if isinstance(slot, dict) else slot.character_name

        self._reorder_party(session.id, group_no, party_no)

        return f"{character_name}을 상비군으로 이동했습니다."

    def add_waiting_member_to_party(
        self,
        guild_id,
        channel_id,
        raid_name,
        waiting_id,
        group_no,
        party_no,
    ):
        session = self._get_active_session(guild_id, channel_id, raid_name)

        waiting = self.waiting_repository.get_by_id(waiting_id)
        if not waiting:
            raise Exception("상비군 대상이 없습니다.")

        target_members = self.slot_repository.get_by_party(
            session.id,
            group_no,
            party_no,
        )

        if len(target_members) >= 4:
            raise Exception("해당 파티는 이미 가득 찼습니다.")

        group_members = self.slot_repository.get_by_group(
            session.id,
            group_no,
        )

        waiting_user_id = waiting["user_id"] if isinstance(waiting, dict) else waiting.user_id
        for m in group_members:
            user_id = m["user_id"] if isinstance(m, dict) else m.user_id
            if user_id == waiting_user_id:
                raise Exception("같은 공대에 동일한 유저가 이미 존재합니다.")

        slot_no = len(target_members) + 1

        self.slot_repository.insert(
            PartySlot(
                id=None,
                session_id=session.id,
                guild_id=waiting["guild_id"] if isinstance(waiting, dict) else waiting.guild_id,
                channel_id=waiting["channel_id"] if isinstance(waiting, dict) else waiting.channel_id,
                raid_name=waiting["raid_name"] if isinstance(waiting, dict) else waiting.raid_name,
                group_no=group_no,
                party_no=party_no,
                slot_no=slot_no,
                is_temp_group=False,
                application_id=waiting["application_id"] if isinstance(waiting, dict) else waiting.application_id,
                user_id=waiting["user_id"] if isinstance(waiting, dict) else waiting.user_id,
                user_name=waiting["user_name"] if isinstance(waiting, dict) else waiting.user_name,
                character_name=waiting["character_name"] if isinstance(waiting, dict) else waiting.character_name,
                job=waiting["job"] if isinstance(waiting, dict) else waiting.job,
                item_level=waiting["item_level"] if isinstance(waiting, dict) else waiting.item_level,
                combat_power=waiting["combat_power"] if isinstance(waiting, dict) else waiting.combat_power,
            )
        )

        self.waiting_repository.delete_by_id(waiting_id)

        character_name = waiting["character_name"] if isinstance(waiting, dict) else waiting.character_name
        return f"{character_name}을 {group_no}공대 {party_no}파티로 이동했습니다."

    def _reorder_party(self, session_id, group_no, party_no):
        members = self.slot_repository.get_by_party(
            session_id,
            group_no,
            party_no,
        )

        for idx, member in enumerate(members, start=1):
            slot_id = member["id"] if isinstance(member, dict) else member.id
            self.slot_repository.update_slot_no(
                slot_id=slot_id,
                slot_no=idx,
            )
