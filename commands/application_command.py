import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from views.application_view import RaceView, ServerView
from views.application_result_view import ApplicationResultView


class ApplicationCommand(commands.Cog):
    def __init__(self, bot, service, message_service, setting_service):
        self.bot = bot
        self.service = service
        self.message_service = message_service
        self.setting_service = setting_service

    @app_commands.command(name="신청", description="레이드 신청 또는 신청 내역 확인")
    @app_commands.rename(character_name="캐릭터명")
    @app_commands.describe(character_name="신청 또는 조회할 캐릭터명")
    async def apply(self, interaction: discord.Interaction, character_name: str):
        try:
            if interaction.guild is None:
                await interaction.response.send_message(
                    "서버 채널에서만 사용할 수 있습니다.",
                    ephemeral=True,
                )
                return

            setting = self.setting_service.get_guild_setting(interaction.guild.id)

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

            await self._process(
                interaction,
                character_name,
                setting.default_race,
                setting.default_server,
                show_identity=False,
            )

        except Exception as exc:
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content=f"오류가 발생했습니다: {exc}",
                    embed=None,
                    view=None,
                )
            else:
                await interaction.response.send_message(
                    f"오류가 발생했습니다: {exc}",
                    ephemeral=True,
                )

    async def _process(self, interaction, character_name, race, server, show_identity: bool):
        await interaction.response.defer(ephemeral=True)

        try:
            if interaction.guild is None or interaction.channel is None:
                await interaction.edit_original_response(
                    content="서버 채널에서만 사용할 수 있습니다.",
                    embed=None,
                    view=None,
                )
                return

            result = await asyncio.to_thread(
                self.service.process,
                interaction.guild.id,
                interaction.channel.id,
                interaction.user.id,
                interaction.user.name,
                character_name,
                race,
                server,
            )

            if result["action"] == "created":
                embed = self.message_service.build_application_result_embed(
                    result["raid_name"],
                    result["info"],
                    "created",
                    show_identity=show_identity,
                )

                await interaction.channel.send(embed=embed)

                await interaction.edit_original_response(
                    content="신청이 완료되었습니다.",
                    embed=None,
                    view=None,
                )

            elif result["action"] == "show_current":
                embed = self.message_service.build_application_result_embed(
                    result["raid_name"],
                    result["info"],
                    "updated",
                    show_identity=show_identity,
                )
                view = ApplicationResultView(
                    application_service=self.service,
                    application_id=result["application"].id,
                    owner_user_id=interaction.user.id,
                )
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=view,
                )

            elif result["action"] == "show_all":
                embed = self.message_service.build_application_all_embed(
                    result["info"],
                    result["applications"],
                    show_identity=show_identity,
                )
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=None,
                )

            else:
                await interaction.edit_original_response(
                    content=result["message"],
                    embed=None,
                    view=None,
                )

        except Exception as exc:
            await interaction.edit_original_response(
                content=f"오류가 발생했습니다: {exc}",
                embed=None,
                view=None,
            )
