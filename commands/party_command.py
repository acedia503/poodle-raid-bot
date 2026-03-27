# commands/party_command.py

import traceback

import discord
from discord import app_commands
from discord.ext import commands

from views.party_view import 
    PartyBuildHomeView,
    build_party_result_embed,
    build_empty_result_embed,
)


class PartyCommand(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        raid_service,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
    ):
        self.bot = bot
        self.raid_service = raid_service
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service

    
    @app_commands.command(name="공대", description="공대 관리")
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
    
        result = self.party_manage_service.get_active_build_result(
            guild_id=guild.id,
            channel_id=channel.id,
        )
    
        if result:
            embed = build_party_result_embed(result)
        else:
            embed = build_empty_result_embed(raid.raid_name)
    
        view = PartyBuildHomeView(
            rule=rule,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
    
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )

        except Exception as e:
            traceback.print_exc()

            if interaction.response.is_done():
                await interaction.followup.send(
                    f"공대 화면을 여는 중 오류가 발생했습니다: {e}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"공대 화면을 여는 중 오류가 발생했습니다: {e}",
                    ephemeral=True,
                )
