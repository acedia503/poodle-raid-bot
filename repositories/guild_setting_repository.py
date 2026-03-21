from typing import Optional

from domain.guild_setting import GuildSetting
from repositories.base_repository import BaseRepository


class GuildSettingRepository(BaseRepository):
    def get_by_guild_id(self, guild_id: int) -> Optional[GuildSetting]:
        # TODO: DB 조회
        raise NotImplementedError

    def upsert(
        self,
        guild_id: int,
        default_race: str | None,
        default_server: str | None,
    ) -> GuildSetting:
        # TODO: insert or update
        raise NotImplementedError

    def delete_by_guild_id(self, guild_id: int) -> bool:
        # TODO: DB 삭제
        raise NotImplementedError
