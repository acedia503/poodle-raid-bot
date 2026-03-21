import discord

from services.message_service import MessageService
from services.setting_service import SettingService


class SettingMainView(discord.ui.View):
    def __init__(
        self,
        setting_service: SettingService,
        message_service: MessageService,
        guild_id: int,
    ):
        super().__init__(timeout=180)
        self.setting_service = setting_service
        self.message_service = message_service
        self.guild_id = guild_id

    @discord.ui.button(label="설정", style=discord.ButtonStyle.primary)
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TODO: 종족/서버 선택 UI로 연결
        await interaction.response.send_message("설정 UI는 TODO", ephemeral=True)

    @discord.ui.button(label="수정", style=discord.ButtonStyle.primary)
    async def update_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("수정 UI는 TODO", ephemeral=True)

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = self.setting_service.delete_guild_setting(self.guild_id)
        msg = "기본 설정이 삭제되었습니다." if ok else "삭제할 기본 설정이 없습니다."
        await interaction.response.send_message(msg, ephemeral=True)
