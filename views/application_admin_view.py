import discord


class AdminApplicationUserSearchModal(discord.ui.Modal, title="유저 검색"):
    keyword = discord.ui.TextInput(
        label="유저 이름",
        required=True,
        max_length=30,
    )

    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, str(self.keyword.value).strip())


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


class ApplicationAdminMainView(discord.ui.View):
    def __init__(self, list_callback, delete_callback):
        super().__init__(timeout=180)
        self.list_callback_func = list_callback
        self.delete_callback_func = delete_callback

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


class ApplicationAdminListView(discord.ui.View):
    def __init__(self, back_callback):
        super().__init__(timeout=180)
        self.back_callback_func = back_callback

    @discord.ui.button(label="뒤로 이동", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.back_callback_func(interaction)

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

    @discord.ui.button(label="유저", style=discord.ButtonStyle.primary)
    async def user_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.by_user_callback(interaction)

    @discord.ui.button(label="캐릭터", style=discord.ButtonStyle.primary)
    async def character_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.by_character_callback(interaction)

    @discord.ui.button(label="뒤로 이동", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.back_callback(interaction)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="신청 관리 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class UserSearchResultSelect(discord.ui.Select):
    def __init__(self, users, select_callback):
        options = [
            discord.SelectOption(
                label=f"{idx}. {user['user_name']}",
                value=str(user["user_id"]),
            )
            for idx, user in enumerate(users[:25], start=1)
        ]

        super().__init__(
            placeholder="유저를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.user_map = {str(user["user_id"]): user for user in users[:25]}
        self.select_callback = select_callback

    async def callback(self, interaction: discord.Interaction):
        selected_user = self.user_map[self.values[0]]
        await self.select_callback(interaction, selected_user)


class ApplicationAdminUserSearchResultView(discord.ui.View):
    def __init__(self, users, select_callback, back_callback):
        super().__init__(timeout=180)
        self.add_item(UserSearchResultSelect(users, select_callback))
        self.back_callback_func = back_callback

    @discord.ui.button(label="뒤로 이동", style=discord.ButtonStyle.secondary, row=3)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.back_callback_func(interaction)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=3)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="신청 관리 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class ApplicationMultiSelect(discord.ui.Select):
    def __init__(self, applications, selected_ids, refresh_callback):
        options = [
            discord.SelectOption(
                label=f"{idx}. {app.character_name} | {app.job} | {app.item_level} | {app.combat_power:,}",
                description=f"{app.user_name}",
                value=str(app.id),
                default=(app.id in selected_ids),
            )
            for idx, app in enumerate(applications[:25], start=1)
        ]

        super().__init__(
            placeholder="신청 내역을 선택하세요",
            min_values=0,
            max_values=max(1, len(options)),
            options=options,
        )

        self.applications = applications
        self.selected_ids = selected_ids
        self.refresh_callback = refresh_callback

    async def callback(self, interaction: discord.Interaction):
        self.selected_ids.clear()
        self.selected_ids.update(int(v) for v in self.values)
        await self.refresh_callback(interaction, self.applications, self.selected_ids)


class SingleDeleteView(discord.ui.View):
    def __init__(self, delete_callback, back_callback):
        super().__init__(timeout=180)
        self.delete_callback_func = delete_callback
        self.back_callback_func = back_callback

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.delete_callback_func(interaction)

    @discord.ui.button(label="뒤로 이동", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.back_callback_func(interaction)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="신청 관리 창을 닫았습니다.",
            embed=None,
            view=None,
        )


class MultiDeleteView(discord.ui.View):
    def __init__(
        self,
        applications,
        selected_ids,
        refresh_callback,
        delete_selected_callback,
        delete_all_callback,
        back_callback,
    ):
        super().__init__(timeout=180)

        self.applications = applications
        self.selected_ids = selected_ids
        self.refresh_callback = refresh_callback
        self.delete_selected_callback = delete_selected_callback
        self.delete_all_callback = delete_all_callback
        self.back_callback = back_callback

        has_applications = len(applications) > 0
        has_selected = len(selected_ids) > 0

        if has_applications:
            self.add_item(
                ApplicationMultiSelect(
                    applications=applications,
                    selected_ids=selected_ids,
                    refresh_callback=refresh_callback,
                )
            )

        self.add_item(DeleteAllButton(self, disabled=not has_applications))
        self.add_item(DeleteSelectedButton(self, disabled=not has_selected))
        self.add_item(BackButton(self))
        self.add_item(CloseButton())


class DeleteAllButton(discord.ui.Button):
    def __init__(self, parent_view, disabled: bool):
        super().__init__(
            label="전체 삭제",
            style=discord.ButtonStyle.danger,
            row=3,
            disabled=disabled,
        )
        self.parent_view_ref = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view_ref.delete_all_callback(interaction)


class DeleteSelectedButton(discord.ui.Button):
    def __init__(self, parent_view, disabled: bool):
        super().__init__(
            label="선택 삭제",
            style=discord.ButtonStyle.danger,
            row=3,
            disabled=disabled,
        )
        self.parent_view_ref = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view_ref.delete_selected_callback(
            interaction,
            list(self.parent_view_ref.selected_ids),
        )


class BackButton(discord.ui.Button):
    def __init__(self, parent_view):
        super().__init__(
            label="뒤로 이동",
            style=discord.ButtonStyle.secondary,
            row=3,
        )
        self.parent_view_ref = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view_ref.back_callback(interaction)


class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="닫기",
            style=discord.ButtonStyle.secondary,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="신청 관리 창을 닫았습니다.",
            embed=None,
            view=None,
        )
