import discord
from discord import app_commands
from discord.ext import commands

from services.party_rule_service import PartyRuleService
# from services.raid_service import RaidService
# from view.party_view import PartyRuleDetailView, build_rule_detail_embed


class PartyCommand(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        raid_service,
        party_rule_service: PartyRuleService,
    ):
        self.bot = bot
        self.raid_service = raid_service
        self.party_rule_service = party_rule_service

    @app_commands.command(name="공대", description="현재 채널의 공대 생성 규칙을 확인합니다.")
    async def party(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel

        if guild is None or channel is None:
            await interaction.response.send_message(
                "길드 채널에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        raid = self.raid_service.get_channel_raid(
            guild_id=guild.id,
            channel_id=channel.id,
        )
        if raid is None:
            await interaction.response.send_message(
                "설정된 레이드가 없습니다.",
                ephemeral=True,
            )
            return

        rule = self.party_rule_service.get_or_create_rule(
            guild_id=guild.id,
            channel_id=channel.id,
            raid_name=raid.raid_name,
        )

        content = self._build_rule_text(rule)
        await interaction.response.send_message(
            content,
            ephemeral=True,
        )

    def _build_rule_text(self, rule) -> str:
        def jobs_to_text(jobs: list[str]) -> str:
            return ", ".join(jobs) if jobs else "없음"

        return (
            "공대 생성 규칙\n\n"
            "1파티\n"
            f"우선 직업: {jobs_to_text(rule.party1_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(rule.party1_preferred_jobs)}\n\n"
            "2파티\n"
            f"우선 직업: {jobs_to_text(rule.party2_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(rule.party2_preferred_jobs)}"
        )


async def setup(bot: commands.Bot):
    from database import db
    from repository.raid_rule_repository import RaidRuleRepository
    from services.party_rule_service import PartyRuleService
    from services.raid_service import RaidService

    raid_rule_repository = RaidRuleRepository(db)
    party_rule_service = PartyRuleService(raid_rule_repository)
    raid_service = RaidService(...)

    await bot.add_cog(
        PartyCommand(
            bot=bot,
            raid_service=raid_service,
            party_rule_service=party_rule_service,
        )
    )
