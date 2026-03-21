from domain.channel_raid import ChannelRaid
from repositories.channel_raid_repository import ChannelRaidRepository
from utils.validators import validate_positive_int


class RaidDuplicateError(Exception):
    pass


class RaidService:
    def __init__(self, channel_raid_repository: ChannelRaidRepository):
        self.channel_raid_repository = channel_raid_repository

    def get_channel_raid(self, channel_id: int) -> ChannelRaid | None:
        return self.channel_raid_repository.get_active_by_channel_id(channel_id)

    def save_channel_raid(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
        min_item_level: int | None = None,
    ) -> ChannelRaid:
        if not raid_name.strip():
            raise ValueError("레이드명은 비어 있을 수 없습니다.")

        if not validate_positive_int(min_item_level):
            raise ValueError("최소 아이템레벨은 0 이상이어야 합니다.")

        duplicated = self.channel_raid_repository.get_by_guild_and_raid_name(
            guild_id=guild_id,
            raid_name=raid_name.strip(),
        )

        if duplicated is not None and duplicated.channel_id != channel_id:
            raise RaidDuplicateError("같은 서버 내에서 동일한 레이드명은 중복 설정할 수 없습니다.")

        channel_raid = ChannelRaid(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name.strip(),
            min_item_level=min_item_level,
            is_active=True,
        )
        return self.channel_raid_repository.upsert(channel_raid)

    def delete_channel_raid(self, channel_id: int) -> bool:
        return self.channel_raid_repository.delete_by_channel_id(channel_id)
