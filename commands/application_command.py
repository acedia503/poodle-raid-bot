import discord
from discord import app_commands
from discord.ext import commands

from services.application_service import (
    ApplicationError,
    ApplicationService,
    CharacterLookupError,
    DuplicateApplicationError,
    EntryConditionFailedError,
    RaidNotLinkedError,
)
from services.message_service import MessageService
from utils.permissions import ensure_guild_only


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

    application_group = app_commands.Group(name="신청", description="레이드 신청 관리")

    @application_group.command(name="생성", description="현재 채널 레이드에 신청")
    @app_commands.describe(character_name="신청할 캐릭터명")
    async def application_create(self, interaction: discord.Interaction, character_name: str):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        try:
            application = self.application_service.apply(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                user_id=interaction.user.id,
                user_name=interaction.user.display_name,
                character_name=character_name,
            )
            embed = self.message_service.build_application_embed(application)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except RaidNotLinkedError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
        except DuplicateApplicationError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
        except CharacterLookupError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
        except EntryConditionFailedError as exc:
            await interaction.response.send_message(f"입장 조건 미달:\n{exc}", ephemeral=True)
        except ApplicationError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)

    @application_group.command(name="조회", description="내 신청 조회")
    async def application_view(self, interaction: discord.Interaction):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
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

        embed = self.message_service.build_application_list_embed(applications)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @application_group.command(name="취소", description="신청 취소")
    @app_commands.describe(application_id="취소할 신청 ID")
    async def application_cancel(self, interaction: discord.Interaction, application_id: int):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        try:
            ok = self.application_service.cancel_application(
                application_id=application_id,
                requester_user_id=interaction.user.id,
                is_admin=False,
            )
            msg = "신청이 취소되었습니다." if ok else "취소할 신청이 없습니다."
            await interaction.response.send_message(msg, ephemeral=True)
        except ApplicationError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
