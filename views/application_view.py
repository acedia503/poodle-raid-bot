import discord

from utils.constants import RACE_SERVERS


class RaceView(discord.ui.View):
    def __init__(self, callback_func):
        super().__init__(timeout=180)
        self.callback_func = callback_func

    @discord.ui.button(label="천족", style=discord.ButtonStyle.primary)
    async def elyos_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_func(interaction, "천족")

    @discord.ui.button(label="마족", style=discord.ButtonStyle.danger)
    async def asmodian_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_func(interaction, "마족")


class ServerSelect(discord.ui.Select):
    def __init__(self, race, callback_func):
        options = [
            discord.SelectOption(label=server["name"], value=server["name"])
            for server in RACE_SERVERS[race]
        ]

        super().__init__(
            placeholder="서버를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )

        self.callback_func = callback_func
        self.race = race

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.race, self.values[0])


class ServerView(discord.ui.View):
    def __init__(self, race, callback_func):
        super().__init__(timeout=180)
        self.add_item(ServerSelect(race, callback_func))
