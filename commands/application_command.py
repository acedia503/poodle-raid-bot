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

    @app_commands.command(name="신청")
    async def apply(self, interaction: discord.Interaction, 캐릭터명: str):
        setting = self.setting_service.get_guild_setting(interaction.guild.id)

        # 기본 설정 없음 → 종족 선택
        if not setting:
            async def race_callback(inter, race):
                await inter.response.send_message(
                    "서버 선택",
                    view=ServerView(race, lambda i, r, s: self._process(i, 캐릭터명, r, s)),
                    ephemeral=True,
                )

            await interaction.response.send_message(
                "종족 선택",
                view=RaceView(race_callback),
                ephemeral=True,
            )
            return

        # 기본 설정 있음
        await self._process(
            interaction,
            캐릭터명,
            setting.default_race,
            setting.default_server,
        )

    async def _process(self, interaction, character_name, race, server):
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
                show_identity=False,
            )
            await interaction.channel.send(text)

        elif result["action"] == "show_all":
            raids = "\n".join(f"- {a.raid_name}" for a in result["applications"])
            text = f"전체 신청 레이드\n\n{raids}"
            await interaction.channel.send(text)

        else:
            await interaction.followup.send(result["message"], ephemeral=True)

        await interaction.delete_original_response()
