from typing import Optional

from domain.party_slot import PartySlot
from repositories.base_repository import BaseRepository


class PartySlotRepository(BaseRepository):
    def bulk_create(self, slots: list[PartySlot]) -> list[PartySlot]:
        raise NotImplementedError

    def get_by_session_id(self, session_id: int) -> list[PartySlot]:
        raise NotImplementedError

    def get_by_position(
        self,
        session_id: int,
        group_no: int,
        party_no: int,
        slot_no: int,
    ) -> Optional[PartySlot]:
        raise NotImplementedError

    def get_by_id(self, slot_id: int) -> Optional[PartySlot]:
        raise NotImplementedError

    def update_slot(self, slot_id: int, **fields) -> bool:
        raise NotImplementedError

    def delete_by_session_id(self, session_id: int) -> int:
        raise NotImplementedError

    def delete_by_id(self, slot_id: int) -> bool:
        raise NotImplementedError
