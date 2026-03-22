import discord

from utils.constants import RAID_PRESETS
from services.raid_service import (
    RaidDeleteBlockedError,
    RaidDuplicateError,
    RaidPresetNotFoundError,
)


class RaidPresetButton(discord.ui.Button):
    def __init__(
        self,
        guild_id,
        channel_id,
        preset,
        raid_service,
        message_service,
        mode="create",
    ):
        super().__init__(label=preset["name"], style=discord.ButtonStyle.primary)
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.preset = preset
        self.raid_service = raid_service
        self.message_service = message_service
        self.mode = mode

    async def callback(self, interaction: discord.Interaction):
        try:
            channel_raid = self.raid_service.save_channel_raid_by_preset(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                raid_name=self.preset["name"],
            )

            embed = self.message_service.build_channel_raid_embed(channel_raid)

            content = (
                "레이드 설정이 수정되었습니다."
                if self.mode == "update"
                else "레이드 설정이 생성되었습니다."
            )

            await interaction.response.edit_message(
                content=content,
                embed=embed,
                view=None,
            )

        except RaidDuplicateError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)

        except RaidPresetNotFoundError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)

        except Exception as exc:
            await interaction.response.send_message(
                f"예상치 못한 오류: {exc}",
                ephemeral=True,
            )


class RaidInitView(discord.ui.View):
    def __init__(
        self,
        guild_id,
        channel_id,
        raid_service,
        message_service,
        mode="create",
    ):
        super().__init__(timeout=180)

        for preset in RAID_PRESETS:
            self.add_item(
                RaidPresetButton(
                    guild_id=guild_id,
                    channel_id=channel_id,
                    preset=preset,
                    raid_service=raid_service,
                    message_service=message_service,
                    mode=mode,
                )
            )

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=4)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="레이드 설정 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class RaidDeleteConfirmView(discord.ui.View):
    def __init__(self, guild_id, channel_id, raid_service):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.raid_service = raid_service

    @discord.ui.button(label="같이 삭제", style=discord.ButtonStyle.danger)
    async def force_delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            result = self.raid_service.force_delete_channel_raid_with_applications(self.channel_id)

            if not result["deleted_raid"]:
                await interaction.response.edit_message(
                    content="삭제할 레이드 설정이 없습니다.",
                    embed=None,
                    view=None,
                )
                return

            await interaction.response.edit_message(
                content=(
                    f"{result['raid_name']} 레이드와 신청자 "
                    f"{result['deleted_applications']}명을 함께 삭제했습니다."
                ),
                embed=None,
                view=None,
            )

        except Exception as exc:
            await interaction.response.send_message(
                f"예상치 못한 오류: {exc}",
                ephemeral=True,
            )

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="레이드 삭제를 취소했습니다.",
            embed=None,
            view=None,
        )


class RaidMainView(discord.ui.View):
    def __init__(
        self,
        guild_id,
        channel_id,
        raid_service,
        message_service,
    ):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.raid_service = raid_service
        self.message_service = message_service

    @discord.ui.button(label="수정", style=discord.ButtonStyle.primary)
    async def update_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RaidInitView(
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            raid_service=self.raid_service,
            message_service=self.message_service,
            mode="update",
        )
        await interaction.response.edit_message(
            content="수정할 레이드 항목을 선택하세요.",
            embed=None,
            view=view,
        )

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            ok = self.raid_service.delete_channel_raid(self.channel_id)

            if ok:
                await interaction.response.edit_message(
                    content="레이드 설정이 삭제되었습니다.",
                    embed=None,
                    view=None,
                )
            else:
                await interaction.response.edit_message(
                    content="삭제할 레이드 설정이 없습니다.",
                    embed=None,
                    view=None,
                )

        except RaidDeleteBlockedError as exc:
            view = RaidDeleteConfirmView(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                raid_service=self.raid_service,
            )
            await interaction.response.edit_message(
                content=(
                    f"현재 레이드에 신청자 {exc.application_count}명이 있어 삭제할 수 없습니다.\n"
                    f"신청자도 같이 삭제하시겠습니까?"
                ),
                embed=None,
                view=view,
            )

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="레이드 설정 창을 닫았습니다.",
            embed=None,
            view=None,
        )
