import discord

from services.application_service import ApplicationService


class ApplicationResultView(discord.ui.View):
    def __init__(self, application_service: ApplicationService, application_id: int, user_id: int):
        super().__init__(timeout=180)
        self.application_service = application_service
        self.application_id = application_id
        self.user_id = user_id

    @discord.ui.button(label="신청 취소", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            ok = self.application_service.cancel_application(
                application_id=self.application_id,
                requester_user_id=self.user_id,
                is_admin=False,
            )
            msg = "신청이 취소되었습니다." if ok else "취소할 신청이 없습니다."
        except Exception as exc:
            msg = str(exc)

        await interaction.response.send_message(msg, ephemeral=True)
