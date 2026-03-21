from typing import Optional

from domain.party_waiting_member import PartyWaitingMember
from repositories.base_repository import BaseRepository


class PartyWaitingRepository(BaseRepository):
    def bulk_create(self, waiting_members: list[PartyWaitingMember]) -> list[PartyWaitingMember]:
        raise NotImplementedError

    def create(self, waiting_member: PartyWaitingMember) -> PartyWaitingMember:
        raise NotImplementedError

    def get_by_session_id(self, session_id: int) -> list[PartyWaitingMember]:
        raise NotImplementedError

    def get_by_session_and_status(self, session_id: int, status: str) -> list[PartyWaitingMember]:
        raise NotImplementedError

    def get_by_id(self, waiting_id: int) -> Optional[PartyWaitingMember]:
        raise NotImplementedError

    def delete_by_session_id(self, session_id: int) -> int:
        raise NotImplementedError

    def delete_by_id(self, waiting_id: int) -> bool:
        raise NotImplementedError
