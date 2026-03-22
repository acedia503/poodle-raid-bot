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

    @app_commands.command(name="신청", description="레이드 신청 또는 신청 내역 확인")
    @app_commands.rename(character_name="캐릭터명")
    @app_commands.describe(character_name="신청 또는 조회할 캐릭터명")
    async def apply(self, interaction: discord.Interaction, character_name: str):
        setting = self.setting_service.get_guild_setting(interaction.guild.id)

        # 기본 설정 없음 → 종족/서버 선택
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

        # 기본 설정 있음 → 바로 처리
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

if result["action"] == "created":
    embed = self.message_service.build_application_result_embed(
        result["raid_name"],
        result["info"],
        "created",
        show_identity=show_identity,
    )
    await interaction.edit_original_response(
        content=None,
        embed=embed,
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
