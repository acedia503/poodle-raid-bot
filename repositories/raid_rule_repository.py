from typing import Optional

from domain.raid_rule import RaidRule
from repositories.base_repository import BaseRepository


class RaidRuleRepository(BaseRepository):
    def get_by_guild_and_raid(self, guild_id: int, raid_name: str) -> Optional[RaidRule]:
        raise NotImplementedError

    def upsert(self, rule: RaidRule) -> RaidRule:
        raise NotImplementedError

    def delete_by_guild_and_raid(self, guild_id: int, raid_name: str) -> bool:
        raise NotImplementedError
