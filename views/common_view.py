import discord


class CloseView(discord.ui.View):
    def __init__(self, timeout: int = 180):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
