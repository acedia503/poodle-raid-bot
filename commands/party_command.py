import discord
from discord import app_commands
from discord.ext import commands

from services.message_service import MessageService
from services.party_builder_service import PartyBuilderService
from services.party_manage_service import PartyManageService
from services.raid_service import RaidService
from utils.permissions import ensure_guild_only, is_admin
from views.party_view import PartyMainView


class PartyCommand(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        raid_service: RaidService,
        party_builder_service: PartyBuilderService,
        party_manage_service: PartyManageService,
        message_service: MessageService,
    ):
        self.bot = bot
        self.raid_service = raid_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.message_service = message_service

    @app_commands.command(name="공대", description="공대 생성/조회/수정/초기화")
    async def party(self, interaction: discord.Interaction):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if not is_admin(interaction):
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        view = PartyMainView(
            raid_service=self.raid_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            message_service=self.message_service,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            user_id=interaction.user.id,
        )
        await interaction.response.send_message("공대 메뉴", view=view, ephemeral=True)
