from typing import Optional

from domain.party_build_session import PartyBuildSession
from repositories.base_repository import BaseRepository


class PartyBuildSessionRepository(BaseRepository):
    def create(self, session: PartyBuildSession) -> PartyBuildSession:
        raise NotImplementedError

    def get_latest_by_channel_and_raid(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
    ) -> Optional[PartyBuildSession]:
        raise NotImplementedError

    def get_by_id(self, session_id: int) -> Optional[PartyBuildSession]:
        raise NotImplementedError

    def delete_by_id(self, session_id: int) -> bool:
        raise NotImplementedError

    def update_status(self, session_id: int, status: str) -> bool:
        raise NotImplementedError
