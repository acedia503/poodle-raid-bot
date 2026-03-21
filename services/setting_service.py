from domain.guild_setting import GuildSetting
from repositories.guild_setting_repository import GuildSettingRepository


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
        self.validate_setting_input(default_race, default_server)
        return self.guild_setting_repository.upsert(
            guild_id=guild_id,
            default_race=default_race,
            default_server=default_server,
        )

    def delete_guild_setting(self, guild_id: int) -> bool:
        return self.guild_setting_repository.delete_by_guild_id(guild_id)

    def validate_setting_input(
        self,
        default_race: str | None,
        default_server: str | None,
    ) -> None:
        # TODO: validators.py 활용
        pass
