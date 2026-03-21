import discord

from services.message_service import MessageService
from services.raid_service import RaidService


class RaidMainView(discord.ui.View):
    def __init__(
        self,
        raid_service: RaidService,
        message_service: MessageService,
        guild_id: int,
        channel_id: int,
    ):
        super().__init__(timeout=180)
        self.raid_service = raid_service
        self.message_service = message_service
        self.guild_id = guild_id
        self.channel_id = channel_id

    @discord.ui.button(label="연결", style=discord.ButtonStyle.primary)
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("레이드 연결 UI는 TODO", ephemeral=True)

    @discord.ui.button(label="수정", style=discord.ButtonStyle.primary)
    async def update_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("레이드 수정 UI는 TODO", ephemeral=True)

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = self.raid_service.delete_channel_raid(self.channel_id)
        msg = "현재 채널 레이드 연결이 삭제되었습니다." if ok else "삭제할 레이드가 없습니다."
        await interaction.response.send_message(msg, ephemeral=True)
