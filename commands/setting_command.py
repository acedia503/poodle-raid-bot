import discord
from discord import app_commands
from discord.ext import commands

from services.message_service import MessageService
from services.setting_service import SettingService
from utils.permissions import ensure_guild_only, is_admin


class SettingCommand(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        setting_service: SettingService,
        message_service: MessageService,
    ):
        self.bot = bot
        self.setting_service = setting_service
        self.message_service = message_service

    setting_group = app_commands.Group(name="설정", description="기본 종족/서버 설정")

    @setting_group.command(name="조회", description="현재 기본 설정 조회")
    async def setting_view(self, interaction: discord.Interaction):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        setting = self.setting_service.get_guild_setting(interaction.guild.id)
        embed = self.message_service.build_guild_setting_embed(setting)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @setting_group.command(name="저장", description="기본 종족/서버 저장")
    @app_commands.describe(default_race="천족 또는 마족", default_server="기본 서버명")
    async def setting_save(
        self,
        interaction: discord.Interaction,
        default_race: str,
        default_server: str,
    ):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if not is_admin(interaction):
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        try:
            setting = self.setting_service.save_guild_setting(
                guild_id=interaction.guild.id,
                default_race=default_race,
                default_server=default_server,
            )
            embed = self.message_service.build_guild_setting_embed(setting)
            await interaction.response.send_message("기본 설정이 저장되었습니다.", embed=embed, ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)

    @setting_group.command(name="삭제", description="기본 설정 삭제")
    async def setting_delete(self, interaction: discord.Interaction):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if not is_admin(interaction):
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        ok = self.setting_service.delete_guild_setting(interaction.guild.id)
        msg = "기본 설정이 삭제되었습니다." if ok else "삭제할 기본 설정이 없습니다."
        await interaction.response.send_message(msg, ephemeral=True)
