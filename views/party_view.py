import discord

from services.message_service import MessageService
from services.party_builder_service import PartyBuilderService
from services.party_manage_service import PartyManageService
from services.raid_service import RaidService


class PartyMainView(discord.ui.View):
    def __init__(
        self,
        raid_service: RaidService,
        party_builder_service: PartyBuilderService,
        party_manage_service: PartyManageService,
        message_service: MessageService,
        guild_id: int,
        channel_id: int,
        user_id: int,
    ):
        super().__init__(timeout=180)
        self.raid_service = raid_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.message_service = message_service
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.user_id = user_id

    @discord.ui.button(label="공대 생성", style=discord.ButtonStyle.primary)
    async def build_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            session = self.party_builder_service.build_party(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                created_by_user_id=self.user_id,
            )
            await interaction.response.send_message(
                f"공대 생성 완료: session_id={session.id}",
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)

    @discord.ui.button(label="결과 확인", style=discord.ButtonStyle.secondary)
    async def result_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_raid = self.raid_service.get_channel_raid(self.channel_id)
        if channel_raid is None:
            await interaction.response.send_message("현재 채널에 레이드가 없습니다.", ephemeral=True)
            return

        session = self.party_manage_service.get_latest_session(
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            raid_name=channel_raid.raid_name,
        )
        if session is None:
            await interaction.response.send_message("공대 생성 결과가 없습니다.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"최신 공대 세션: {session.id}",
            ephemeral=True,
        )

    @discord.ui.button(label="초기화", style=discord.ButtonStyle.danger)
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_raid = self.raid_service.get_channel_raid(self.channel_id)
        if channel_raid is None:
            await interaction.response.send_message("현재 채널에 레이드가 없습니다.", ephemeral=True)
            return

        ok = self.party_manage_service.reset_latest_party(
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            raid_name=channel_raid.raid_name,
        )
        msg = "공대 생성 결과가 초기화되었습니다." if ok else "초기화할 공대 결과가 없습니다."
        await interaction.response.send_message(msg, ephemeral=True)
