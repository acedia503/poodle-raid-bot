# commands/party_command.py

import discord
from discord import app_commands
from discord.ext import commands

from views.party_view import (
    PartyBuildHomeView,
    build_empty_result_embed,
    build_first_status_embed,
)


class PartyCommand(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        raid_service,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
        setting_service,
    ):
        self.bot = bot
        self.raid_service = raid_service
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.setting_service = setting_service

    def _get_show_race_server(self, guild_id: int) -> bool:
        """
        기본 종족/서버 설정이 있으면 False
        없으면 True
        """
        try:
            setting = self.setting_service.get_guild_setting(guild_id)
        except Exception:
            return True

        if setting is None:
            return True

        if isinstance(setting, dict):
            default_race = setting.get("default_race")
            default_server = setting.get("default_server")
        else:
            default_race = getattr(setting, "default_race", None)
            default_server = getattr(setting, "default_server", None)

        has_default_race_server = bool(default_race and default_server)
        return not has_default_race_server

    @app_commands.command(name="공대", description="공대 생성 및 관리")
    async def party(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel

        if guild is None or channel is None:
            await interaction.response.send_message(
                "길드 채널에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        raid = self.raid_service.get_channel_raid(channel.id)
        if raid is None:
            await interaction.response.send_message(
                "설정된 레이드가 없습니다.",
                ephemeral=True,
            )
            return

        rule = self.party_rule_service.get_or_create_rule(
            guild_id=guild.id,
            channel_id=channel.id,
            raid_name=raid.raid_name,
        )

        result = self.party_manage_service.get_active_build_result(
            guild_id=guild.id,
            channel_id=channel.id,
        )

        show_race_server = self._get_show_race_server(guild.id)

        if result:
            embed = build_first_status_embed(
                result,
                show_race_server=show_race_server,
            )
        else:
            embed = build_empty_result_embed(raid.raid_name)

        view = PartyBuildHomeView(
            rule=rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
            show_race_server=show_race_server,
        )

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
