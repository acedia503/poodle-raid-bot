import discord
from discord import app_commands
from discord.ext import commands

from views.party_view import (
    PartyBuildHomeView,
    build_party_result_embed,
    build_empty_result_embed,
)

from services.party_builder_service import PartyBuilderService
from services.party_manage_service import PartyManageService
from services.party_modify_service import PartyModifyService
from services.party_rule_service import PartyRuleService
from services.application_service import ApplicationService

from repositories.channel_raid_repository import ChannelRaidRepository
from repositories.raid_application_repository import RaidApplicationRepository
from repositories.party_build_session_repository import PartyBuildSessionRepository
from repositories.party_slot_repository import PartySlotRepository
from repositories.party_waiting_repository import PartyWaitingMemberRepository
from repositories.raid_rule_repository import RaidRuleRepository

from database import Database


class PartyCommand(commands.Cog):
    def __init__(self, bot: commands.Bot, db):
        self.bot = bot
        self.db = db


        self.channel_raid_repo = ChannelRaidRepository(self.db)
        self.application_repo = RaidApplicationRepository(self.db)

        self.session_repo = PartyBuildSessionRepository(self.db)
        self.slot_repo = PartySlotRepository(self.db)
        self.waiting_repo = PartyWaitingMemberRepository(self.db)
        self.rule_repo = PartyRuleRepository(self.db)

        # =========================
        # Service
        # =========================
        self.application_service = ApplicationService(self.application_repo)

        self.party_rule_service = PartyRuleService(self.rule_repo)

        self.party_builder_service = PartyBuilderService(
            application_service=self.application_service,
            party_rule_service=self.party_rule_service,
            session_repository=self.session_repo,
            slot_repository=self.slot_repo,
            waiting_repository=self.waiting_repo,
        )

        self.party_manage_service = PartyManageService(
            session_repository=self.session_repo,
            slot_repository=self.slot_repo,
            waiting_repository=self.waiting_repo,
        )

        self.party_modify_service = PartyModifyService(
            slot_repository=self.slot_repo,
            waiting_repository=self.waiting_repo,
            session_repository=self.session_repo,
        )

    # =========================
    # /공대
    # =========================
    @app_commands.command(name="공대", description="공대 생성 및 관리")
    async def party(self, interaction: discord.Interaction):

        guild_id = interaction.guild.id
        channel_id = interaction.channel.id

        # 1. 채널 레이드 확인
        raid = self.channel_raid_repo.get_channel_raid(
            channel_id=channel_id
        )

        if not raid:
            await interaction.response.send_message(
                "설정된 레이드가 없습니다.",
                ephemeral=True,
            )
            return

        # 2. 현재 공대 상태 조회
        result = self.party_manage_service.get_active_build_result(
            guild_id,
            channel_id,
        )

        if result:
            embed = build_party_result_embed(result)
        else:
            embed = build_empty_result_embed(raid.raid_name)

        # 3. View 생성
        view = PartyBuildHomeView(
            rule=raid,
            rule_service=self.party_rule_service,
            builder=self.party_builder_service,
            manage=self.party_manage_service,
            modify=self.party_modify_service,
        )

        await interaction.response.send_message(embed=embed, view=view)


# =========================
# Cog 등록
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(PartyCommand(bot))
