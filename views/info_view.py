import discord

from services.character_info_service import CharacterInfoError, CharacterInfoService
from services.message_service import MessageService
from utils.constants import RACE_SERVERS


class RaceButtonView(discord.ui.View):
    def __init__(
        self,
        character_name: str,
        info_service: CharacterInfoService,
        message_service: MessageService,
    ):
        super().__init__(timeout=180)
        self.character_name = character_name
        self.info_service = info_service
        self.message_service = message_service

    @discord.ui.button(label="천족", style=discord.ButtonStyle.primary)
    async def elyos_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_race = "천족"
        view = ServerSelectView(
            character_name=self.character_name,
            race=selected_race,
            info_service=self.info_service,
            message_service=self.message_service,
        )
        await interaction.response.edit_message(
            content=f"캐릭터명: **{self.character_name}**\n종족: **{selected_race}**\n서버를 선택하세요.",
            view=view,
            embed=None,
        )

    @discord.ui.button(label="마족", style=discord.ButtonStyle.danger)
    async def asmodian_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_race = "마족"
        view = ServerSelectView(
            character_name=self.character_name,
            race=selected_race,
            info_service=self.info_service,
            message_service=self.message_service,
        )
        await interaction.response.edit_message(
            content=f"캐릭터명: **{self.character_name}**\n종족: **{selected_race}**\n서버를 선택하세요.",
            view=view,
            embed=None,
        )


class ServerSelect(discord.ui.Select):
    def __init__(
        self,
        character_name: str,
        race: str,
        info_service: CharacterInfoService,
        message_service: MessageService,
    ):
        servers = RACE_SERVERS.get(race, [])
        options = [
            discord.SelectOption(label=server["name"], value=server["name"])
            for server in servers
        ]

        super().__init__(
            placeholder="서버를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )

        self.character_name = character_name
        self.race = race
        self.info_service = info_service
        self.message_service = message_service

    async def callback(self, interaction: discord.Interaction):
        selected_server = self.values[0]

        try:
            info = self.info_service.get_character_info(
                character_name=self.character_name,
                race=self.race,
                server=selected_server,
            )
            embed = self.message_service.build_character_info_embed(info)
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=None,
            )
        except CharacterInfoError as exc:
            await interaction.response.edit_message(
                content=f"조회 실패: {exc}",
                embed=None,
                view=None,
            )


class ServerSelectView(discord.ui.View):
    def __init__(
        self,
        character_name: str,
        race: str,
        info_service: CharacterInfoService,
        message_service: MessageService,
    ):
        super().__init__(timeout=180)
        self.add_item(
            ServerSelect(
                character_name=character_name,
                race=race,
                info_service=info_service,
                message_service=message_service,
            )
        )
