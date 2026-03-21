import discord

from utils.constants import RACE_SERVERS


class SettingInitRaceView(discord.ui.View):
    def __init__(self, guild_id, setting_service, message_service):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.setting_service = setting_service
        self.message_service = message_service

    @discord.ui.button(label="천족", style=discord.ButtonStyle.primary)
    async def elyos_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingServerSelectView(
            guild_id=self.guild_id,
            selected_race="천족",
            setting_service=self.setting_service,
            message_service=self.message_service,
        )
        await interaction.response.edit_message(
            content="종족: **천족**\n서버를 선택하세요.",
            view=view,
            embed=None,
        )

    @discord.ui.button(label="마족", style=discord.ButtonStyle.danger)
    async def asmodian_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingServerSelectView(
            guild_id=self.guild_id,
            selected_race="마족",
            setting_service=self.setting_service,
            message_service=self.message_service,
        )
        await interaction.response.edit_message(
            content="종족: **마족**\n서버를 선택하세요.",
            view=view,
            embed=None,
        )


class SettingServerSelect(discord.ui.Select):
    def __init__(self, guild_id, selected_race, setting_service, message_service):
        self.guild_id = guild_id
        self.selected_race = selected_race
        self.setting_service = setting_service
        self.message_service = message_service

        servers = RACE_SERVERS.get(selected_race, [])
        options = [
            discord.SelectOption(label=server["name"], value=server["name"])
            for server in servers
        ]

        super().__init__(
            placeholder="서버를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_server = self.values[0]

        setting = self.setting_service.save_guild_setting(
            guild_id=self.guild_id,
            default_race=self.selected_race,
            default_server=selected_server,
        )

        embed = self.message_service.build_guild_setting_embed(setting)
        view = SettingSavedView()

        await interaction.response.edit_message(
            content="기본 설정이 저장되었습니다.",
            embed=embed,
            view=view,
        )


class SettingServerSelectView(discord.ui.View):
    def __init__(self, guild_id, selected_race, setting_service, message_service):
        super().__init__(timeout=180)
        self.add_item(
            SettingServerSelect(
                guild_id=guild_id,
                selected_race=selected_race,
                setting_service=setting_service,
                message_service=message_service,
            )
        )


class SettingSavedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="설정 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class SettingMainView(discord.ui.View):
    def __init__(self, guild_id, setting_service, message_service):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.setting_service = setting_service
        self.message_service = message_service

    @discord.ui.button(label="수정", style=discord.ButtonStyle.primary)
    async def update_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingInitRaceView(
            guild_id=self.guild_id,
            setting_service=self.setting_service,
            message_service=self.message_service,
        )
        await interaction.response.edit_message(
            content="종족을 다시 선택하세요.",
            embed=None,
            view=view,
        )

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok = self.setting_service.delete_guild_setting(self.guild_id)
        msg = "기본 설정이 삭제되었습니다." if ok else "삭제할 설정이 없습니다."

        await interaction.response.edit_message(
            content=msg,
            embed=None,
            view=None,
        )

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="설정 창을 닫았습니다.",
            embed=None,
            view=None,
        )
