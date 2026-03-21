import discord

from services.application_service import ApplicationService


class ApplicationAdminMainView(discord.ui.View):
    def __init__(self, application_service: ApplicationService):
        super().__init__(timeout=180)
        self.application_service = application_service

    @discord.ui.button(label="신청 생성", style=discord.ButtonStyle.primary)
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("관리자 신청 생성 UI는 TODO", ephemeral=True)

    @discord.ui.button(label="신청 조회", style=discord.ButtonStyle.secondary)
    async def view_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("관리자 신청 조회 UI는 TODO", ephemeral=True)

    @discord.ui.button(label="신청 삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("관리자 신청 삭제 UI는 TODO", ephemeral=True)
