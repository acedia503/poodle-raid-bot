import discord


class ApplicationCharacterModal(discord.ui.Modal, title="신규 신청"):
    character_name = discord.ui.TextInput(
        label="캐릭터명",
        placeholder="신청할 캐릭터명을 입력하세요.",
        required=True,
        max_length=30,
    )

    def __init__(self, submit_callback):
        super().__init__()
        self.submit_callback = submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.submit_callback(interaction, str(self.character_name.value).strip())


class ApplicationMainView(discord.ui.View):
    def __init__(
        self,
        application_count: int,
        apply_callback,
        cancel_callback,
        select_cancel_callback,
        cancel_all_callback,
        status_callback,
        admin_delete_callback=None,
    ):
        super().__init__(timeout=180)

        self.application_count = application_count
        self.apply_callback = apply_callback
        self.cancel_callback = cancel_callback
        self.select_cancel_callback = select_cancel_callback
        self.cancel_all_callback = cancel_all_callback
        self.status_callback = status_callback
        self.admin_delete_callback = admin_delete_callback

        self.add_item(NewApplyButton(self))

        if application_count == 1:
            self.add_item(CancelButton(self))
        elif application_count >= 2:
            self.add_item(SelectCancelButton(self))
            self.add_item(CancelAllButton(self))

        self.add_item(StatusButton(self))

        if admin_delete_callback is not None:
            self.add_item(AdminDeleteButton(self))


class NewApplyButton(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="신규 신청", style=discord.ButtonStyle.primary)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.apply_callback(interaction)


class CancelButton(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="신청 취소", style=discord.ButtonStyle.danger)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.cancel_callback(interaction)


class SelectCancelButton(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="선택 취소", style=discord.ButtonStyle.danger)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.select_cancel_callback(interaction)


class CancelAllButton(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="전체 취소", style=discord.ButtonStyle.danger)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.cancel_all_callback(interaction)


class StatusButton(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="레이드 신청 현황", style=discord.ButtonStyle.secondary)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.status_callback(interaction)


class AdminDeleteButton(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="관리자용 신청 삭제", style=discord.ButtonStyle.danger, row=1)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.admin_delete_callback(interaction)
