import discord


class AdminApplicationDeleteCharacterModal(discord.ui.Modal, title="캐릭터명 검색"):
    character_name = discord.ui.TextInput(
        label="캐릭터명",
        required=True,
        max_length=30,
    )

    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, str(self.character_name.value).strip())


class ConfirmDeleteView(discord.ui.View):
    def __init__(self, application, delete_callback):
        super().__init__(timeout=60)
        self.application = application
        self.delete_callback = delete_callback

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.delete_callback(interaction, self.application.id)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="삭제가 취소되었습니다.",
            embed=None,
            view=None,
        )
