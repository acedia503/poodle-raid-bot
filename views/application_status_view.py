import discord


class ApplicationStatusSearchModal(discord.ui.Modal):
    keyword = discord.ui.TextInput(
        label="검색어",
        placeholder="검색할 유저명 또는 캐릭터명을 입력하세요.",
        required=True,
        max_length=30,
    )

    def __init__(self, title: str, submit_callback):
        super().__init__(title=title)
        self.submit_callback = submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.submit_callback(
            interaction,
            str(self.keyword.value).strip(),
        )


class ApplicationStatusView(discord.ui.View):
    def __init__(
        self,
        user_search_callback,
        character_search_callback,
        back_callback,
        admin_delete_callback=None,
    ):
        super().__init__(timeout=180)

        self.user_search_callback = user_search_callback
        self.character_search_callback = character_search_callback
        self.back_callback = back_callback
        self.admin_delete_callback = admin_delete_callback

        self.add_item(UserSearchButton(self))
        self.add_item(CharacterSearchButton(self))

        if admin_delete_callback is not None:
            self.add_item(AdminDeleteButton(self))

        self.add_item(BackButton(self))


class UserSearchButton(discord.ui.Button):
    def __init__(self, view_ref):
        super().__init__(
            label="유저명 검색",
            style=discord.ButtonStyle.secondary,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.user_search_callback(interaction)


class CharacterSearchButton(discord.ui.Button):
    def __init__(self, view_ref):
        super().__init__(
            label="캐릭터명 검색",
            style=discord.ButtonStyle.secondary,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.character_search_callback(interaction)


class AdminDeleteButton(discord.ui.Button):
    def __init__(self, view_ref):
        super().__init__(
            label="관리자용 삭제",
            style=discord.ButtonStyle.danger,
            row=1,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.admin_delete_callback(interaction)


class BackButton(discord.ui.Button):
    def __init__(self, view_ref):
        super().__init__(
            label="뒤로 가기",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.back_callback(interaction)
