import discord
from discord import app_commands
from discord.ext import commands

from services.message_service import MessageService
from services.setting_service import SettingService
from utils.permissions import ensure_guild_only, is_admin
from views.setting_view import SettingInitRaceView, SettingMainView


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

    @app_commands.command(name="설정", description="기본 종족 및 서버 설정")
    async def setting(self, interaction: discord.Interaction):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message(
                "서버 채널에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        if not is_admin(interaction):
            await interaction.response.send_message(
                "관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        setting = self.setting_service.get_guild_setting(interaction.guild.id)

        if setting is None:
            view = SettingInitRaceView(
                guild_id=interaction.guild.id,
                setting_service=self.setting_service,
                message_service=self.message_service,
            )
            await interaction.response.send_message(
                content="기본 설정이 없습니다.\n종족을 선택하세요.",
                view=view,
                ephemeral=True,
            )
            return

        embed = self.message_service.build_guild_setting_embed(setting)
        view = SettingMainView(
            guild_id=interaction.guild.id,
            setting_service=self.setting_service,
            message_service=self.message_service,
        )
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
