# commands/refresh_command.py

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils.constants import REFRESH_CONCURRENCY_LIMIT
from utils.permissions import is_admin


class RefreshCommand(commands.Cog):
    def __init__(self, bot: commands.Bot, application_service):
        self.bot = bot
        self.application_service = application_service

    async def _refresh_many(self, applications: list) -> tuple[list, list]:
        semaphore = asyncio.Semaphore(REFRESH_CONCURRENCY_LIMIT)
        success = []
        failed = []

        async def worker(application):
            async with semaphore:
                try:
                    info = await self.application_service.refresh_character_and_applications(
                        application
                    )
                    success.append((application, info))
                except Exception as exc:
                    failed.append((application, exc))

        await asyncio.gather(*(worker(application) for application in applications))
        return success, failed

    def _build_self_result_embed(self, success: list, failed: list) -> discord.Embed:
        if not success and not failed:
            return discord.Embed(
                title="내 캐릭터 정보 갱신",
                description="갱신할 신청 내역이 없습니다.",
                color=discord.Color.orange(),
            )

        lines = [
            f"{idx}. {application.character_name} / {info['item_level']} / {info['combat_power']:,}"
            for idx, (application, info) in enumerate(success, start=1)
        ]
        for application, exc in failed:
            lines.append(f"❌ {application.character_name} - 갱신 실패: {exc}")

        return discord.Embed(
            title="내 캐릭터 정보 갱신",
            description="\n".join(lines),
            color=discord.Color.green() if not failed else discord.Color.orange(),
        )

    @app_commands.command(name="갱신", description="아툴 캐릭터 정보를 최신으로 갱신합니다.")
    @app_commands.rename(target="대상")
    @app_commands.describe(
        target="비워두면 본인 신청 내역만 갱신됩니다. '전체' 선택 시 관리자만 사용 가능하며 서버 전체 신청자를 갱신합니다."
    )
    @app_commands.choices(target=[app_commands.Choice(name="전체", value="all")])
    async def refresh(
        self,
        interaction: discord.Interaction,
        target: app_commands.Choice[str] | None = None,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "서버 채널에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        refresh_all = target is not None and target.value == "all"

        if refresh_all and not is_admin(interaction):
            await interaction.response.send_message(
                "관리자만 전체 갱신을 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        if refresh_all:
            identities = await asyncio.to_thread(
                self.application_service.get_distinct_character_applications_for_guild,
                interaction.guild.id,
            )

            success, failed = await self._refresh_many(identities)

            for application, exc in failed:
                print(f"[갱신][전체] {application.character_name} 갱신 실패: {exc}")

            await interaction.edit_original_response(
                content="모든 캐릭터 정보가 갱신되었습니다. 신청 현황을 통해 확인해주세요.",
                embed=None,
            )
            return

        identities = await asyncio.to_thread(
            self.application_service.get_distinct_character_applications_for_user,
            interaction.guild.id,
            interaction.user.id,
        )

        success, failed = await self._refresh_many(identities)

        embed = self._build_self_result_embed(success, failed)
        await interaction.edit_original_response(embed=embed)
