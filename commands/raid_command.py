import discord
from discord import app_commands
from discord.ext import commands

from services.message_service import MessageService
from services.raid_service import RaidService
from utils.permissions import ensure_guild_only, is_admin
from views.raid_view import RaidInitView, RaidMainView


class RaidCommand(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        raid_service: RaidService,
        message_service: MessageService,
    ):
        self.bot = bot
        self.raid_service = raid_service
        self.message_service = message_service

    @app_commands.command(name="레이드", description="현재 채널 레이드 설정")
    async def raid(self, interaction: discord.Interaction):
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

        channel_raid = self.raid_service.get_channel_raid(interaction.channel.id)

        if channel_raid is None:
            view = RaidInitView(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                raid_service=self.raid_service,
                message_service=self.message_service,
                mode="create",
            )
            await interaction.response.send_message(
                content="현재 채널에 레이드 설정이 없습니다.\n레이드 항목을 선택하세요.",
                view=view,
                ephemeral=True,
            )
            return

        embed = self.message_service.build_channel_raid_embed(channel_raid)
        view = RaidMainView(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            raid_service=self.raid_service,
            message_service=self.message_service,
        )
        await interaction.response.send_message(
            content="현재 채널 레이드 설정입니다.",
            embed=embed,
            view=view,
            ephemeral=True,
        )
