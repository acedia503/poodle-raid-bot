import discord

from services.character_info_service import CharacterInfoError, CharacterInfoService
from services.message_service import MessageService
from utils.constants import SERVER_OPTIONS


class RaceSelect(discord.ui.Select):
    def __init__(self, character_name: str, info_service: CharacterInfoService, message_service: MessageService):
        options = [
            discord.SelectOption(label="천족", value="천족"),
            discord.SelectOption(label="마족", value="마족"),
        ]
        super().__init__(placeholder="종족을 선택하세요", min_values=1, max_values=1, options=options)
        self.character_name = character_name
        self.info_service = info_service
        self.message_service = message_service

    async def callback(self, interaction: discord.Interaction):
        selected_race = self.values[0]
        view = ServerSelectView(
            character_name=self.character_name,
            race=selected_race,
            info_service=self.info_service,
            message_service=self.message_service,
        )
        await interaction.response.edit_message(
            content=f"종족: **{selected_race}** 선택됨\n이제 서버를 선택하세요.",
            view=view,
            embed=None,
        )


class RaceSelectView(discord.ui.View):
    def __init__(self, character_name: str, info_service: CharacterInfoService, message_service: MessageService):
        super().__init__(timeout=180)
        self.add_item(RaceSelect(character_name, info_service, message_service))


class ServerSelect(discord.ui.Select):
    def __init__(
        self,
        character_name: str,
        race: str,
        info_service: CharacterInfoService,
        message_service: MessageService,
    ):
        options = [discord.SelectOption(label=name, value=name) for name in SERVER_OPTIONS]
        super().__init__(placeholder="서버를 선택하세요", min_values=1, max_values=1, options=options)
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
        self.add_item(ServerSelect(character_name, race, info_service, message_service))
