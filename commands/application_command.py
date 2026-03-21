import discord
from discord import app_commands
from discord.ext import commands

from views.application_view import RaceView, ServerView


class ApplicationCommand(commands.Cog):
    def __init__(self, bot, service, message_service, setting_service):
        self.bot = bot
        self.service = service
        self.message_service = message_service
        self.setting_service = setting_service

    @app_commands.command(name="신청", description="레이드 신청 및 확인")
    @app_commands.rename(character_name="캐릭터명")
    @app_commands.describe(character_name="신청 또는 조회할 캐릭터명")
    async def apply(self, interaction: discord.Interaction, character_name: str):
        setting = self.setting_service.get_guild_setting(interaction.guild.id)

        # 기본 설정 없음 → 종족 선택 UI
        if not setting:
            async def race_callback(inter, race):
                await inter.response.edit_message(
                    content=f"종족: **{race}**\n서버를 선택하세요.",
                    view=ServerView(
                        race,
                        lambda i, r, s: self._process(i, character_name, r, s, show_identity=True),
                    ),
                    embed=None,
                )

            await interaction.response.send_message(
                content="기본 서버 설정이 없습니다.\n종족을 선택하세요.",
                view=RaceView(race_callback),
                ephemeral=True,
            )
            return

        # 기본 설정 있음
        await self._process(
            interaction,
            character_name,
            setting.default_race,
            setting.default_server,
            show_identity=False,
        )

    async def _process(self, interaction, character_name, race, server, show_identity: bool):
        await interaction.response.defer(ephemeral=True)

        result = self.service.process(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            user_id=interaction.user.id,
            user_name=interaction.user.name,
            character_name=character_name,
            race=race,
            server=server,
        )

        if result["action"] in ["created", "show_current"]:
            text = self.message_service.build_application_result_text(
                result["raid_name"],
                result["info"],
                "created" if result["action"] == "created" else "updated",
                show_identity=show_identity,
            )
            await interaction.channel.send(text)

        elif result["action"] == "show_all":
            text = self.message_service.build_application_all_result_text(
                result["info"],
                result["applications"],
                show_identity=show_identity,
            )
            await interaction.channel.send(text)

        else:
            await interaction.followup.send(result["message"], ephemeral=True)

        await interaction.delete_original_response()
