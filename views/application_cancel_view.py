import discord


class ApplicationCancelSelect(discord.ui.Select):
    def __init__(self, applications, selected_ids, refresh_callback):
        options = [
            discord.SelectOption(
                label=f"{idx}. {app.raid_name} | {app.character_name}",
                description=f"{app.job} | {app.item_level} | {app.combat_power:,}",
                value=str(app.id),
                default=(app.id in selected_ids),
            )
            for idx, app in enumerate(applications[:25], start=1)
        ]

        super().__init__(
            placeholder="취소할 신청 내역을 선택하세요",
            min_values=0,
            max_values=max(1, len(options)),
            options=options,
        )

        self.applications = applications
        self.selected_ids = selected_ids
        self.refresh_callback = refresh_callback

    async def callback(self, interaction: discord.Interaction):
        self.selected_ids.clear()
        self.selected_ids.update(int(value) for value in self.values)

        await self.refresh_callback(
            interaction,
            self.applications,
            self.selected_ids,
        )


class ApplicationCancelSelectView(discord.ui.View):
    def __init__(
        self,
        applications,
        selected_ids,
        refresh_callback,
        cancel_selected_callback,
        cancel_all_callback,
    ):
        super().__init__(timeout=180)

        self.applications = applications
        self.selected_ids = selected_ids
        self.refresh_callback = refresh_callback
        self.cancel_selected_callback = cancel_selected_callback
        self.cancel_all_callback = cancel_all_callback

        self.add_item(
            ApplicationCancelSelect(
                applications=applications,
                selected_ids=selected_ids,
                refresh_callback=refresh_callback,
            )
        )

    @discord.ui.button(label="선택 취소", style=discord.ButtonStyle.danger, row=3)
    async def cancel_selected_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cancel_selected_callback(
            interaction,
            list(self.selected_ids),
        )

    @discord.ui.button(label="전체 취소", style=discord.ButtonStyle.danger, row=3)
    async def cancel_all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cancel_all_callback(interaction)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=3)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="신청 취소 창을 닫았습니다.",
            embed=None,
            view=None,
        )
