import discord
from discord import app_commands
from discord.ext import commands

from services.character_info_service import CharacterInfoService
from services.message_service import MessageService
from utils.permissions import ensure_guild_only
from views.info_view import RaceButtonView


class InfoCommand(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        character_info_service: CharacterInfoService,
        message_service: MessageService,
    ):
        self.bot = bot
        self.character_info_service = character_info_service
        self.message_service = message_service

    @app_commands.command(name="정보", description="캐릭터 정보 조회")
    @app_commands.describe(character_name="조회할 캐릭터명")
    async def info(self, interaction: discord.Interaction, character_name: str):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message("서버 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return

        view = RaceButtonView(
            character_name=character_name,
            info_service=self.character_info_service,
            message_service=self.message_service,
        )
        await interaction.response.send_message(
            content=f"캐릭터명: **{character_name}**\n종족을 선택하세요.",
            view=view,
            ephemeral=True,
        )
