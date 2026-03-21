import discord
from discord import app_commands
from discord.ext import commands

from services.application_service import ApplicationService, ApplicationError
from services.message_service import MessageService
from utils.permissions import ensure_guild_only
from views.application_view import ApplicationResultView


class ApplicationCommand(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        application_service: ApplicationService,
        message_service: MessageService,
    ):
        self.bot = bot
        self.application_service = application_service
        self.message_service = message_service

    @app_commands.command(name="신청", description="레이드 신청 또는 조회")
    @app_commands.describe(character_name="신청할 캐릭터명")
    async def application(
        self,
        interaction: discord.Interaction,
        character_name: str | None = None,
    ):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if character_name:
            try:
                application = self.application_service.apply(
                    guild_id=interaction.guild.id,
                    channel_id=interaction.channel.id,
                    user_id=interaction.user.id,
                    user_name=interaction.user.display_name,
                    character_name=character_name,
                )
                embed_data = self.message_service.build_application_embed(application)
                view = ApplicationResultView(
                    application_service=self.application_service,
                    application_id=application.id,
                    user_id=interaction.user.id,
                )
                await interaction.response.send_message(str(embed_data), view=view, ephemeral=True)
                return
            except ApplicationError as exc:
                await interaction.response.send_message(str(exc), ephemeral=True)
                return

        applications = self.application_service.get_my_application_in_current_channel(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            user_id=interaction.user.id,
        )
        if not applications:
            applications = self.application_service.get_user_applications(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
            )

        embed_data = self.message_service.build_application_list_embed(applications)
        await interaction.response.send_message(str(embed_data), ephemeral=True)
