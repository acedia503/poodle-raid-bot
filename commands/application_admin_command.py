import discord
from discord import app_commands
from discord.ext import commands

from services.application_service import ApplicationService
from utils.permissions import ensure_guild_only, is_admin
from views.application_admin_view import ApplicationAdminMainView


class ApplicationAdminCommand(commands.Cog):
    def __init__(self, bot: commands.Bot, application_service: ApplicationService):
        self.bot = bot
        self.application_service = application_service

    @app_commands.command(name="신청관리", description="관리자가 특정 유저 신청을 관리합니다.")
    @app_commands.describe(target_user="대상 유저", character_name="캐릭터명")
    async def application_admin(
        self,
        interaction: discord.Interaction,
        target_user: discord.Member,
        character_name: str | None = None,
    ):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if not is_admin(interaction):
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        view = ApplicationAdminMainView(application_service=self.application_service)
        await interaction.response.send_message(
            f"대상 유저: {target_user.display_name}\n캐릭터명: {character_name or '-'}",
            view=view,
            ephemeral=True,
        )
