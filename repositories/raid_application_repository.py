from typing import Optional

from domain.raid_application import RaidApplication
from repositories.base_repository import BaseRepository


class RaidApplicationRepository(BaseRepository):
    def create(self, application: RaidApplication) -> RaidApplication:
        raise NotImplementedError

    def delete_by_id(self, application_id: int) -> bool:
        raise NotImplementedError

    def get_by_id(self, application_id: int) -> Optional[RaidApplication]:
        raise NotImplementedError

    def get_by_guild_raid_character(
        self,
        guild_id: int,
        raid_name: str,
        character_name: str,
    ) -> Optional[RaidApplication]:
        raise NotImplementedError

    def get_user_application_in_raid(
        self,
        guild_id: int,
        user_id: int,
        raid_name: str,
    ) -> list[RaidApplication]:
        raise NotImplementedError

    def get_user_applications(self, guild_id: int, user_id: int) -> list[RaidApplication]:
        raise NotImplementedError

    def get_applications_by_raid(
        self,
        guild_id: int,
        raid_name: str,
        statuses: list[str] | None = None,
    ) -> list[RaidApplication]:
        raise NotImplementedError

    def update_status(self, application_id: int, status: str) -> bool:
        raise NotImplementedError

    def bulk_update_status(self, application_ids: list[int], status: str) -> int:
        raise NotImplementedError

    def get_by_ids(self, application_ids: list[int]) -> list[RaidApplication]:
        raise NotImplementedError
