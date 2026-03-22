import discord


class ApplicationResultView(discord.ui.View):
    def __init__(self, application_service, application_id: int, owner_user_id: int):
        super().__init__(timeout=180)
        self.application_service = application_service
        self.application_id = application_id
        self.owner_user_id = owner_user_id

    @discord.ui.button(label="신청 취소", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message(
                "본인의 신청만 취소할 수 있습니다.",
                ephemeral=True,
            )
            return

        try:
            ok = self.application_service.cancel_application(
                application_id=self.application_id,
                requester_user_id=interaction.user.id,
                is_admin=False,
            )

            if ok:
                await interaction.response.edit_message(
                    content="신청이 취소되었습니다.",
                    embed=None,
                    view=None,
                )
            else:
                await interaction.response.edit_message(
                    content="이미 취소되었거나 존재하지 않는 신청입니다.",
                    embed=None,
                    view=None,
                )

        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message(
                "명령 실행자만 닫을 수 있습니다.",
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(
            content="신청 창을 닫았습니다.",
            embed=None,
            view=None,
        )
