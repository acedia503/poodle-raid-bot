from domain.channel_raid import ChannelRaid
from repositories.channel_raid_repository import ChannelRaidRepository
from utils.validators import validate_positive_int


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
        min_combat_power: int | None = None,
        entry_condition_text: str | None = None,
    ) -> ChannelRaid:
        if not raid_name.strip():
            raise ValueError("레이드명은 비어 있을 수 없습니다.")

        if not validate_positive_int(min_item_level):
            raise ValueError("최소 아이템레벨은 0 이상이어야 합니다.")

        if not validate_positive_int(min_combat_power):
            raise ValueError("최소 전투력은 0 이상이어야 합니다.")

        channel_raid = ChannelRaid(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name.strip(),
            min_item_level=min_item_level,
            min_combat_power=min_combat_power,
            entry_condition_text=entry_condition_text.strip() if entry_condition_text else None,
            is_active=True,
        )
        return self.channel_raid_repository.upsert(channel_raid)

    def delete_channel_raid(self, channel_id: int) -> bool:
        return self.channel_raid_repository.delete_by_channel_id(channel_id)

    def validate_entry_condition(
        self,
        channel_raid: ChannelRaid,
        item_level: int,
        combat_power: int,
    ) -> tuple[bool, list[str]]:
        errors: list[str] = []

        if channel_raid.min_item_level is not None and item_level < channel_raid.min_item_level:
            errors.append(f"최소 아이템레벨 {channel_raid.min_item_level} 이상 필요")

        if channel_raid.min_combat_power is not None and combat_power < channel_raid.min_combat_power:
            errors.append(f"최소 전투력 {channel_raid.min_combat_power} 이상 필요")

        return (len(errors) == 0, errors)
