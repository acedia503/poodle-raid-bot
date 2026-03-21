from typing import Optional

from domain.channel_raid import ChannelRaid
from repositories.base_repository import BaseRepository


class ChannelRaidRepository(BaseRepository):
    def get_by_channel_id(self, channel_id: int) -> Optional[ChannelRaid]:
        raise NotImplementedError

    def get_active_by_channel_id(self, channel_id: int) -> Optional[ChannelRaid]:
        raise NotImplementedError

    def upsert(self, channel_raid: ChannelRaid) -> ChannelRaid:
        raise NotImplementedError

    def delete_by_channel_id(self, channel_id: int) -> bool:
        raise NotImplementedError

    def deactivate_by_channel_id(self, channel_id: int) -> bool:
        raise NotImplementedError
