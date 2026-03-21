import discord
from discord import app_commands
from discord.ext import commands

from services.message_service import MessageService
from services.raid_service import RaidService
from utils.permissions import ensure_guild_only, is_admin


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

    raid_group = app_commands.Group(name="레이드", description="현재 채널 레이드 설정")

    @raid_group.command(name="조회", description="현재 채널 레이드 조회")
    async def raid_view(self, interaction: discord.Interaction):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        channel_raid = self.raid_service.get_channel_raid(interaction.channel.id)
        embed = self.message_service.build_channel_raid_embed(channel_raid)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @raid_group.command(name="저장", description="현재 채널에 레이드 연결")
    @app_commands.describe(
        raid_name="레이드명",
        min_item_level="최소 아이템레벨",
        min_combat_power="최소 전투력",
        entry_condition_text="기타 입장 조건",
    )
    async def raid_save(
        self,
        interaction: discord.Interaction,
        raid_name: str,
        min_item_level: int | None = None,
        min_combat_power: int | None = None,
        entry_condition_text: str | None = None,
    ):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if not is_admin(interaction):
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        try:
            channel_raid = self.raid_service.save_channel_raid(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                raid_name=raid_name,
                min_item_level=min_item_level,
                min_combat_power=min_combat_power,
                entry_condition_text=entry_condition_text,
            )
            embed = self.message_service.build_channel_raid_embed(channel_raid)
            await interaction.response.send_message("현재 채널 레이드가 저장되었습니다.", embed=embed, ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)

    @raid_group.command(name="삭제", description="현재 채널 레이드 연결 삭제")
    async def raid_delete(self, interaction: discord.Interaction):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        if not is_admin(interaction):
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        ok = self.raid_service.delete_channel_raid(interaction.channel.id)
        msg = "현재 채널 레이드 연결이 삭제되었습니다." if ok else "삭제할 레이드가 없습니다."
        await interaction.response.send_message(msg, ephemeral=True)
