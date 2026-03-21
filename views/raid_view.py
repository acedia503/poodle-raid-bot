import discord

from utils.constants import RAID_OPTIONS
from services.raid_service import RaidDuplicateError


class RaidConditionModal(discord.ui.Modal, title="입장 조건 입력"):
    min_item_level = discord.ui.TextInput(
        label="최소 아이템레벨",
        required=False,
        default="",
    )

    def __init__(self, guild_id, channel_id, raid_name, raid_service, message_service, after_save_view_type="saved"):
        super().__init__()
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.raid_name = raid_name
        self.raid_service = raid_service
        self.message_service = message_service
        self.after_save_view_type = after_save_view_type

    async def on_submit(self, interaction: discord.Interaction):
        try:
            min_il = int(self.min_item_level.value) if self.min_item_level.value.strip() else None

            channel_raid = self.raid_service.save_channel_raid(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                raid_name=self.raid_name,
                min_item_level=min_il,
            )

            embed = self.message_service.build_channel_raid_embed(channel_raid)

            if self.after_save_view_type == "main":
                view = RaidMainView(
                    guild_id=self.guild_id,
                    channel_id=self.channel_id,
                    raid_service=self.raid_service,
                    message_service=self.message_service,
                )
            else:
                view = RaidSavedView()

            await interaction.response.edit_message(
                content="레이드 설정이 저장되었습니다.",
                embed=embed,
                view=view,
            )

        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)

        except RaidDuplicateError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)


class RaidSelect(discord.ui.Select):
    def __init__(self, guild_id, channel_id, raid_service, message_service, after_save_view_type="saved"):
        options = [discord.SelectOption(label=name, value=name) for name in RAID_OPTIONS]
        super().__init__(
            placeholder="레이드명을 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.raid_service = raid_service
        self.message_service = message_service
        self.after_save_view_type = after_save_view_type

    async def callback(self, interaction: discord.Interaction):
        selected_raid_name = self.values[0]
        modal = RaidConditionModal(
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            raid_name=selected_raid_name,
            raid_service=self.raid_service,
            message_service=self.message_service,
            after_save_view_type=self.after_save_view_type,
        )
        await interaction.response.send_modal(modal)


class RaidInitView(discord.ui.View):
    def __init__(self, guild_id, channel_id, raid_service, message_service, after_save_view_type="saved"):
        super().__init__(timeout=180)
        self.add_item(
            RaidSelect(
                guild_id=guild_id,
                channel_id=channel_id,
                raid_service=raid_service,
                message_service=message_service,
                after_save_view_type=after_save_view_type,
            )
        )


class RaidSavedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="레이드 설정 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class RaidMainView(discord.ui.View):
    def __init__(self, guild_id, channel_id, raid_service, message_service):
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
            after_save_view_type="main",
        )
        await interaction.response.edit_message(
            content="레이드명과 입장조건을 다시 설정하세요.",
            embed=None,
            view=view,
        )

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = self.raid_service.delete_channel_raid(self.channel_id)
        msg = "레이드 설정이 삭제되었습니다." if ok else "삭제할 레이드 설정이 없습니다."
        await interaction.response.edit_message(
            content=msg,
            embed=None,
            view=None,
        )

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="레이드 설정 창을 닫았습니다.",
            embed=None,
            view=None,
        )
