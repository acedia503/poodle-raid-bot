import discord
from utils.constants import RACE_SERVERS


class RaceView(discord.ui.View):
    def __init__(self, callback):
        super().__init__()
        self.callback_func = callback

    @discord.ui.button(label="천족")
    async def elyos(self, interaction, button):
        await self.callback_func(interaction, "천족")

    @discord.ui.button(label="마족")
    async def asmo(self, interaction, button):
        await self.callback_func(interaction, "마족")


class ServerSelect(discord.ui.Select):
    def __init__(self, race, callback):
        options = [
            discord.SelectOption(label=s["name"], value=s["name"])
            for s in RACE_SERVERS[race]
        ]
        super().__init__(options=options)
        self.callback_func = callback
        self.race = race

    async def callback(self, interaction):
        await self.callback_func(interaction, self.race, self.values[0])


class ServerView(discord.ui.View):
    def __init__(self, race, callback):
        super().__init__()
        self.add_item(ServerSelect(race, callback))
