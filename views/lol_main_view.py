import discord


class LolApplicationModal(discord.ui.Modal, title="롤 신청"):
    riot_id = discord.ui.TextInput(
        label="롤 아이디",
        placeholder="Acedia#KR1",
        required=True,
        max_length=50,
    )

    def __init__(self, submit_callback):
        super().__init__()
        self.submit_callback = submit_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.submit_callback(
            interaction,
            str(self.riot_id.value),
        )


class LolMainView(discord.ui.View):
    def __init__(
        self,
        apply_callback,
        cancel_callback,
        list_callback,
        reset_callback=None,
    ):
        super().__init__(timeout=180)

        self.apply_callback = apply_callback
        self.cancel_callback = cancel_callback
        self.list_callback = list_callback
        self.reset_callback = reset_callback

        self.add_item(LolApplyButton(self))
        self.add_item(LolCancelButton(self))
        self.add_item(LolListButton(self))

        if reset_callback is not None:
            self.add_item(LolResetButton(self))


class LolApplyButton(discord.ui.Button):
    def __init__(self, view_ref: LolMainView):
        super().__init__(
            label="신청",
            style=discord.ButtonStyle.primary,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.apply_callback(interaction)


class LolCancelButton(discord.ui.Button):
    def __init__(self, view_ref: LolMainView):
        super().__init__(
            label="취소",
            style=discord.ButtonStyle.danger,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.cancel_callback(interaction)


class LolListButton(discord.ui.Button):
    def __init__(self, view_ref: LolMainView):
        super().__init__(
            label="목록",
            style=discord.ButtonStyle.secondary,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.list_callback(interaction)


class LolResetButton(discord.ui.Button):
    def __init__(self, view_ref: LolMainView):
        super().__init__(
            label="초기화",
            style=discord.ButtonStyle.danger,
            row=1,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.reset_callback(interaction)


class LolBackButton(discord.ui.Button):
    def __init__(self, view_ref):
        super().__init__(
            label="돌아가기",
            style=discord.ButtonStyle.secondary,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.back_callback(interaction)


class LolCancelConfirmView(discord.ui.View):
    def __init__(self, confirm_callback, back_callback):
        super().__init__(timeout=180)

        self.confirm_callback = confirm_callback
        self.back_callback = back_callback

        self.add_item(LolCancelConfirmButton(self))
        self.add_item(LolBackButton(self))


class LolCancelConfirmButton(discord.ui.Button):
    def __init__(self, view_ref: LolCancelConfirmView):
        super().__init__(
            label="취소 확정",
            style=discord.ButtonStyle.danger,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.confirm_callback(interaction)


class LolResetConfirmView(discord.ui.View):
    def __init__(self, confirm_callback, back_callback):
        super().__init__(timeout=180)

        self.confirm_callback = confirm_callback
        self.back_callback = back_callback

        self.add_item(LolResetConfirmButton(self))
        self.add_item(LolBackButton(self))


class LolResetConfirmButton(discord.ui.Button):
    def __init__(self, view_ref: LolResetConfirmView):
        super().__init__(
            label="초기화 확정",
            style=discord.ButtonStyle.danger,
        )
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        await self.view_ref.confirm_callback(interaction)
