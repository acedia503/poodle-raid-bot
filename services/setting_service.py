from domain.guild_setting import GuildSetting
from repositories.guild_setting_repository import GuildSettingRepository
from utils.validators import validate_race, validate_server


class SettingService:
    def __init__(self, guild_setting_repository: GuildSettingRepository):
        self.guild_setting_repository = guild_setting_repository

    def get_guild_setting(self, guild_id: int) -> GuildSetting | None:
        return self.guild_setting_repository.get_by_guild_id(guild_id)

    def save_guild_setting(
        self,
        guild_id: int,
        default_race: str | None,
        default_server: str | None,
    ) -> GuildSetting:
        if not validate_race(default_race):
            raise ValueError("유효하지 않은 종족입니다. 천족 또는 마족만 가능합니다.")

        if not validate_server(default_server):
            raise ValueError("유효하지 않은 서버명입니다.")

        return self.guild_setting_repository.upsert(
            guild_id=guild_id,
            default_race=default_race,
            default_server=default_server,
        )

    def delete_guild_setting(self, guild_id: int) -> bool:
        return self.guild_setting_repository.delete_by_guild_id(guild_id)
