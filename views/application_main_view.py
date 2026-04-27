import discord


class ApplicationCharacterModal(discord.ui.Modal, title="신규 신청"):
    character_name = discord.ui.TextInput(
        label="캐릭터명",
        placeholder="신청할 캐릭터명을 입력하세요.",
        required=True,
        max_length=30,
    )

    def __init__(self, submit_callback):
        super().__init__()
        self.submit_callback = submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.submit_callback(
            interaction,
            str(self.character_name.value).strip(),
        )


class ApplicationMainView(discord.ui.View):
    def __init__(
        self,
        apply_callback,
        cancel_callback,
        status_callback,
        admin_delete_callback=None,
    ):
        super().__init__(timeout=180)
        self.apply_callback = apply_callback
        self.cancel_callback = cancel_callback
        self.status_callback = status_callback
        self.admin_delete_callback = admin_delete_callback

        if admin_delete_callback is not None:
            self.add_item(AdminDeleteButton(self))

    @discord.ui.button(label="신규 신청", style=discord.ButtonStyle.primary)
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_callback(interaction)

    @discord.ui.button(label="신청 취소", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cancel_callback(interaction)

    @discord.ui.button(label="레이드 신청 현황", style=discord.ButtonStyle.secondary)
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.status_callback(interaction)


class AdminDeleteButton(discord.ui.Button):
    def __init__(self, parent_view: ApplicationMainView):
        super().__init__(
            label="관리자용 신청 삭제",
            style=discord.ButtonStyle.danger,
            row=1,
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.admin_delete_callback(interaction)
