import discord


class ApplicationCancelButtonSelectView(discord.ui.View):
    def __init__(
        self,
        applications,
        selected_ids,
        refresh_callback,
        cancel_selected_callback,
        back_callback,
    ):
        super().__init__(timeout=180)

        self.applications = applications
        self.selected_ids = selected_ids
        self.refresh_callback = refresh_callback
        self.cancel_selected_callback = cancel_selected_callback
        self.back_callback = back_callback

        for idx, app in enumerate(applications[:8], start=1):
            self.add_item(ApplicationToggleButton(self, idx, app))

        self.add_item(CancelSelectedButton(self))
        self.add_item(BackButton(self))


class ApplicationToggleButton(discord.ui.Button):
    def __init__(self, parent, index: int, application):
        selected = application.id in parent.selected_ids
        super().__init__(
            label=str(index),
            style=discord.ButtonStyle.success if selected else discord.ButtonStyle.secondary,
            row=0 if index <= 5 else 1,
        )
        self.parent = parent
        self.application = application

    async def callback(self, interaction: discord.Interaction):
        if self.application.id in self.parent.selected_ids:
            self.parent.selected_ids.remove(self.application.id)
        else:
            self.parent.selected_ids.add(self.application.id)

        await self.parent.refresh_callback(
            interaction,
            self.parent.applications,
            self.parent.selected_ids,
        )


class CancelSelectedButton(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="선택 취소", style=discord.ButtonStyle.danger, row=2)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.cancel_selected_callback(
            interaction,
            list(self.parent.selected_ids),
        )


class BackButton(discord.ui.Button):
    def __init__(self, parent):
        super().__init__(label="뒤로 가기", style=discord.ButtonStyle.secondary, row=2)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        await self.parent.back_callback(interaction)
