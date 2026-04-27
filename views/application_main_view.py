import discord


class ApplicationCharacterModal(discord.ui.Modal, title="레이드 신청"):
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
        my_applications_callback,
        status_callback,
        close_message: str = "신청 창을 닫았습니다.",
    ):
        super().__init__(timeout=180)
        self.apply_callback = apply_callback
        self.my_applications_callback = my_applications_callback
        self.status_callback = status_callback
        self.close_message = close_message

    @discord.ui.button(label="신청하기", style=discord.ButtonStyle.primary)
    async def apply_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.apply_callback(interaction)

    @discord.ui.button(label="내 신청 확인", style=discord.ButtonStyle.secondary)
    async def my_applications_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.my_applications_callback(interaction)

    @discord.ui.button(label="신청 현황", style=discord.ButtonStyle.secondary)
    async def status_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.status_callback(interaction)

    ##@discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    ##async def close_button(
    ##    self,
    ##    interaction: discord.Interaction,
    ##    button: discord.ui.Button,
    ##):
    ##    await interaction.response.edit_message(
    ##        content=self.close_message,
    ##        embed=None,
    ##        view=None,
    ##    )
