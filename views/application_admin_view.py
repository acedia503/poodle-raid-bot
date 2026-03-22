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


class SelectAllButton(discord.ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="전체 선택", style=discord.ButtonStyle.primary, row=3)
        self.parent_view_ref = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view_ref.selected_ids.clear()
        self.parent_view_ref.selected_ids.update(
            app.id for app in self.parent_view_ref.applications if app.id is not None
        )
        await self.parent_view_ref.refresh_callback(
            interaction,
            self.parent_view_ref.applications,
            self.parent_view_ref.selected_ids,
        )


class ForceDeleteButton(discord.ui.Button):
    def __init__(self, parent_view, disabled: bool):
        super().__init__(
            label="강제 삭제",
            style=discord.ButtonStyle.danger,
            row=3,
            disabled=disabled,
        )
        self.parent_view_ref = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view_ref.delete_callback(
            interaction,
            list(self.parent_view_ref.selected_ids),
        )


class CancelManageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="취소", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="신청 관리 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class AdminApplicationDeleteManageView(discord.ui.View):
    def __init__(
        self,
        applications,
        selected_ids,
        refresh_callback,
        delete_callback,
        allow_select_all: bool,
    ):
        super().__init__(timeout=180)
        self.applications = applications
        self.selected_ids = selected_ids
        self.refresh_callback = refresh_callback
        self.delete_callback = delete_callback
        self.allow_select_all = allow_select_all

        has_applications = len(applications) > 0
        has_selected = len(selected_ids) > 0

        if has_applications:
            self.add_item(
                AdminApplicationDeleteMultiSelect(
                    applications=applications,
                    selected_ids=selected_ids,
                    refresh_callback=refresh_callback,
                )
            )

        if self.allow_select_all and has_applications:
            self.add_item(SelectAllButton(self))

        self.add_item(
            ForceDeleteButton(
                self,
                disabled=(not has_applications or not has_selected),
            )
        )
        self.add_item(CancelManageButton())


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

    class AdminApplicationUserSearchModal(discord.ui.Modal, title="디코 유저 검색"):
        keyword = discord.ui.TextInput(
            label="디코 이름 또는 닉네임",
            required=True,
            max_length=30,
        )
    
        def __init__(self, callback_func):
            super().__init__()
            self.callback_func = callback_func
    
        async def on_submit(self, interaction: discord.Interaction):
            await self.callback_func(interaction, str(self.keyword.value).strip())
    
    
    class AdminApplicationUserResultSelect(discord.ui.Select):
        def __init__(self, members, callback_func):
            options = [
                discord.SelectOption(
                    label=f"{member.display_name} | {member.name}",
                    value=str(member.id),
                )
                for member in members[:25]
            ]
    
            super().__init__(
                placeholder="신청할 디스코드 유저를 선택하세요",
                min_values=1,
                max_values=1,
                options=options,
            )
            self.members = {str(member.id): member for member in members[:25]}
            self.callback_func = callback_func
    
        async def callback(self, interaction: discord.Interaction):
            selected_member = self.members[self.values[0]]
            await self.callback_func(interaction, selected_member)
    
    
    class AdminApplicationUserResultView(discord.ui.View):
        def __init__(self, members, callback_func):
            super().__init__(timeout=180)
            self.add_item(AdminApplicationUserResultSelect(members, callback_func))
