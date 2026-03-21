from domain.channel_raid import ChannelRaid
from repositories.channel_raid_repository import ChannelRaidRepository
from utils.constants import RAID_PRESETS


class RaidDuplicateError(Exception):
    pass


class RaidPresetNotFoundError(Exception):
    pass


class RaidService:
    def __init__(self, channel_raid_repository: ChannelRaidRepository):
        self.channel_raid_repository = channel_raid_repository

    def get_channel_raid(self, channel_id: int) -> ChannelRaid | None:
        return self.channel_raid_repository.get_active_by_channel_id(channel_id)

    def get_raid_preset_by_name(self, raid_name: str) -> dict:
        for preset in RAID_PRESETS:
            if preset["name"] == raid_name:
                return preset
        raise RaidPresetNotFoundError("존재하지 않는 레이드 항목입니다.")

    def save_channel_raid_by_preset(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
    ) -> ChannelRaid:
        preset = self.get_raid_preset_by_name(raid_name)

        duplicated = self.channel_raid_repository.get_by_guild_and_raid_name(
            guild_id=guild_id,
            raid_name=raid_name,
        )

        if duplicated is not None and duplicated.channel_id != channel_id:
            raise RaidDuplicateError("디스코드 서버 내 동일한 레이드명은 중복 설정할 수 없습니다.")

        channel_raid = ChannelRaid(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=preset["name"],
            min_item_level=preset["min_item_level"],
            is_active=True,
        )
        return self.channel_raid_repository.upsert(channel_raid)

    def delete_channel_raid(self, channel_id: int) -> bool:
        return self.channel_raid_repository.delete_by_channel_id(channel_id)
