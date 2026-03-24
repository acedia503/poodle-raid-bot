import discord
from discord import app_commands
from discord.ext import commands

from services.party_rule_service import PartyRuleService
from view.party_view import PartyRuleDetailView, build_rule_detail_embed


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

        raid = self.raid_service.get_channel_raid(channel.id)
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

        embed = build_rule_detail_embed(rule)
        view = PartyRuleDetailView(
            rule=rule,
            party_rule_service=self.party_rule_service,
        )

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
