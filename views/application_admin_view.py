import asyncio

import discord

from views.application_view import RaceView, ServerView


class AdminApplicationCharacterModal(discord.ui.Modal, title="캐릭터명 입력"):
    character_name = discord.ui.TextInput(
        label="캐릭터명",
        required=True,
        max_length=30,
    )

    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, str(self.character_name.value).strip())


class AdminApplicationDeleteCharacterModal(discord.ui.Modal, title="캐릭터명 검색"):
    character_name = discord.ui.TextInput(
        label="캐릭터명",
        required=True,
        max_length=30,
    )

    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, str(self.character_name.value).strip())


class AdminApplicationUserSelect(discord.ui.UserSelect):
    def __init__(self, callback_func):
        super().__init__(
            placeholder="디스코드 유저를 선택하세요",
            min_values=1,
            max_values=1,
        )
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        user = self.values[0]
        await self.callback_func(interaction, user)


class AdminApplicationUserSelectView(discord.ui.View):
    def __init__(self, callback_func):
        super().__init__(timeout=180)
        self.add_item(AdminApplicationUserSelect(callback_func))


class AdminApplicationDeleteMultiSelect(discord.ui.Select):
    def __init__(self, applications, selected_ids, refresh_callback):
        self.applications = applications
        self.selected_ids = selected_ids
        self.refresh_callback = refresh_callback

        options = [
            discord.SelectOption(
                label=f"{app.character_name} | {app.job} | {app.item_level} | {app.combat_power:,}",
                description=f"{app.user_name}",
                value=str(app.id),
                default=(app.id in self.selected_ids),
            )
            for app in applications[:25]
        ]

        super().__init__(
            placeholder="삭제할 캐릭터를 선택하세요",
            min_values=0,
            max_values=max(1, len(options)),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.selected_ids.clear()
        self.selected_ids.update(int(v) for v in self.values)
        await self.refresh_callback(interaction, self.applications, self.selected_ids)


class AdminApplicationDeleteManageView(discord.ui.View):
    def __init__(
        self,
        applications,
        selected_ids,
        refresh_callback,
        delete_callback,
    ):
        super().__init__(timeout=180)
        self.applications = applications
        self.selected_ids = selected_ids
        self.refresh_callback = refresh_callback
        self.delete_callback = delete_callback

        if applications:
            self.add_item(
                AdminApplicationDeleteMultiSelect(
                    applications=applications,
                    selected_ids=selected_ids,
                    refresh_callback=refresh_callback,
                )
            )

    @discord.ui.button(label="전체 선택", style=discord.ButtonStyle.primary, row=3)
    async def select_all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.selected_ids.clear()
        self.selected_ids.update(app.id for app in self.applications if app.id is not None)
        await self.refresh_callback(interaction, self.applications, self.selected_ids)

    @discord.ui.button(label="강제 삭제", style=discord.ButtonStyle.danger, row=3)
    async def force_delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.delete_callback(interaction, list(self.selected_ids))

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=3)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="신청 관리 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class ApplicationAdminMainView(discord.ui.View):
    def __init__(self, add_callback, list_callback, delete_callback):
        super().__init__(timeout=180)
        self.add_callback_func = add_callback
        self.list_callback_func = list_callback
        self.delete_callback_func = delete_callback

    @discord.ui.button(label="추가", style=discord.ButtonStyle.primary)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.add_callback_func(interaction)

    @discord.ui.button(label="목록", style=discord.ButtonStyle.primary)
    async def list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.list_callback_func(interaction)

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.delete_callback_func(interaction)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="신청 관리 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class ApplicationAdminDeleteModeView(discord.ui.View):
    def __init__(self, by_user_callback, by_character_callback, back_callback):
        super().__init__(timeout=180)
        self.by_user_callback = by_user_callback
        self.by_character_callback = by_character_callback
        self.back_callback = back_callback

    @discord.ui.button(label="유저로 검색", style=discord.ButtonStyle.primary)
    async def user_search_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.by_user_callback(interaction)

    @discord.ui.button(label="캐릭터명으로 검색", style=discord.ButtonStyle.primary)
    async def character_search_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.by_character_callback(interaction)

    @discord.ui.button(label="뒤로", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.back_callback(interaction)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="신청 관리 창을 닫았습니다.",
            embed=None,
            view=None,
        )
