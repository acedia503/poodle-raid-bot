import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils.permissions import is_admin

from views.application_view import RaceView, ServerView
from views.application_result_view import ApplicationResultView
from views.application_main_view import ApplicationMainView, ApplicationCharacterModal
from views.application_cancel_view import ApplicationCancelButtonSelectView
from views.application_status_view import ApplicationStatusSearchModal


class ApplicationCommand(commands.Cog):
    def __init__(
        self,
        bot,
        service,
        message_service,
        setting_service,
        party_manage_service,
        party_waiting_repository,
    ):
        self.bot = bot
        self.service = service
        self.message_service = message_service
        self.setting_service = setting_service
        self.party_manage_service = party_manage_service
        self.party_waiting_repository = party_waiting_repository

    def _notice_embed(self, title: str, description: str, color=None) -> discord.Embed:
        return discord.Embed(
            title=title,
            description=description,
            color=color or discord.Color.blurple(),
        )

    def _error_embed(self, title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=title,
            description=description,
            color=discord.Color.red(),
        )

    def _friendly_error_message(self, exc: Exception) -> str:
        text = str(exc)

        if "캐릭터를 찾을 수 없습니다" in text:
            return "캐릭터 정보를 찾을 수 없습니다.\n\n입력한 캐릭터명, 종족, 서버가 맞는지 확인해주세요."

        if "외부 API" in text or "API" in text:
            return "캐릭터 정보 조회 중 문제가 발생했습니다.\n\n잠시 후 다시 시도해주세요.\n계속 실패하면 관리자에게 문의해주세요."

        if "알 수 없는 종족" in text or "알 수 없는 서버" in text:
            return "종족 또는 서버 정보가 올바르지 않습니다.\n\n다시 선택 후 신청해주세요."

        return f"처리 중 예상하지 못한 오류가 발생했습니다.\n\n오류 내용: {text}"

    async def _respond_error(self, interaction: discord.Interaction, exc: Exception):
        embed = self._error_embed(
            "오류가 발생했습니다.",
            self._friendly_error_message(exc),
        )

        if interaction.response.is_done():
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=None,
            )
        else:
            await interaction.response.send_message(
                content=None,
                embed=embed,
                ephemeral=True,
            )

    def _get_show_identity(self, guild_id: int) -> bool:
        setting = self.setting_service.get_guild_setting(guild_id)
        return not bool(setting and setting.default_race and setting.default_server)

    def _format_application_line(
        self,
        idx: int,
        app,
        show_identity: bool,
        include_user_name: bool = False,
        include_raid_name: bool = False,
    ) -> str:
        parts = []

        if include_raid_name:
            parts.append(f"**{app.raid_name}**")

        if include_user_name:
            parts.append(app.user_name)

        parts.append(app.character_name)

        if show_identity:
            parts.append(app.race)
            parts.append(app.server)

        parts.extend([
            app.job,
            str(app.item_level),
            f"{app.combat_power:,}",
        ])

        return f"{idx}. " + " | ".join(parts)

    def _build_my_applications_embed(
        self,
        title: str,
        applications,
        show_identity: bool,
        include_raid_name: bool,
    ) -> discord.Embed:
        if not applications:
            return discord.Embed(
                title=title,
                description="신청 내역이 없습니다.",
                color=discord.Color.blurple(),
            )

        lines = [
            self._format_application_line(
                idx=idx,
                app=app,
                show_identity=show_identity,
                include_raid_name=include_raid_name,
            )
            for idx, app in enumerate(applications, start=1)
        ]

        return discord.Embed(
            title=title,
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )

    def _build_cancel_select_embed(
        self,
        applications,
        selected_ids,
        show_identity: bool,
    ) -> discord.Embed:
        lines = []

        for idx, app in enumerate(applications, start=1):
            mark = "✅" if app.id in selected_ids else "⬜"
            text = self._format_application_line(
                idx=idx,
                app=app,
                show_identity=show_identity,
            )
            text = text.replace(f"{idx}. ", f"{mark} {idx}. ", 1)

            if app.id in selected_ids:
                text = f"**{text}**"

            lines.append(text)

        return discord.Embed(
            title="신청 취소 대상 선택",
            description="\n".join(lines) if lines else "취소할 신청 내역이 없습니다.",
            color=discord.Color.orange(),
        )

    def _build_status_embed(
        self,
        raid_name: str,
        applications,
        show_identity: bool,
        keyword: str | None = None,
        search_label: str | None = None,
    ) -> discord.Embed:
        title = f"{raid_name} 신청 현황"
        if search_label:
            title += f" - {search_label}"

        if applications:
            lines = [
                self._format_application_line(
                    idx=idx,
                    app=app,
                    show_identity=show_identity,
                    include_user_name=True,
                )
                for idx, app in enumerate(applications, start=1)
            ]
            description = "\n".join(lines)
        else:
            description = "신청 내역이 없습니다."

        if keyword:
            description = f"검색어: `{keyword}`\n\n{description}"

        return discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple(),
        )

    async def _render_main(
        self,
        interaction: discord.Interaction,
        *,
        first_response: bool,
    ):
        if interaction.guild is None or interaction.channel is None:
            embed = self._error_embed(
                "사용할 수 없는 위치입니다.",
                "서버 채널에서만 사용할 수 있습니다.",
            )
            if first_response:
                await interaction.response.send_message(
                    content=None,
                    embed=embed,
                    ephemeral=True,
                )
            else:
                await interaction.response.edit_message(
                    content=None,
                    embed=embed,
                    view=None,
                )
            return

        channel_raid = self.service.raid_service.get_channel_raid(interaction.channel.id)
        show_identity = self._get_show_identity(interaction.guild.id)

        if channel_raid is not None:
            applications = await asyncio.to_thread(
                self.service.repository.get_by_guild_raid_and_user_id,
                interaction.guild.id,
                channel_raid.raid_name,
                interaction.user.id,
            )
            title = f"내 {channel_raid.raid_name} 신청 현황"
            include_raid_name = False
        else:
            applications = await asyncio.to_thread(
                self.service.repository.get_by_guild_and_user_id,
                interaction.guild.id,
                interaction.user.id,
            )
            title = "내 전체 신청 현황"
            include_raid_name = True

        embed = self._build_my_applications_embed(
            title=title,
            applications=applications,
            show_identity=show_identity,
            include_raid_name=include_raid_name,
        )

        if channel_raid is None:
            embed.add_field(
                name="안내",
                value="현재 채널에 매칭된 레이드가 없어 전체 신청 현황만 표시합니다.",
                inline=False,
            )

            if first_response:
                await interaction.response.send_message(
                    content=None,
                    embed=embed,
                    ephemeral=True,
                )
            else:
                await interaction.response.edit_message(
                    content=None,
                    embed=embed,
                    view=None,
                )
            return

        async def apply_callback(inter: discord.Interaction):
            async def on_character_submit(
                modal_inter: discord.Interaction,
                character_name: str,
            ):
                setting = self.setting_service.get_guild_setting(modal_inter.guild.id)

                if not setting:
                    async def race_callback(race_inter, race):
                        race_embed = discord.Embed(
                            title="신규 신청",
                            description=(
                                f"**캐릭터명** : {character_name}\n"
                                f"**종족** : {race}\n\n"
                                "서버를 선택하세요."
                            ),
                            color=discord.Color.blurple(),
                        )

                        await race_inter.response.edit_message(
                            content=None,
                            embed=race_embed,
                            view=ServerView(
                                race,
                                lambda i, r, s: self._process(
                                    i,
                                    character_name,
                                    r,
                                    s,
                                    show_identity=True,
                                ),
                            ),
                        )

                    race_embed = discord.Embed(
                        title="신규 신청",
                        description=(
                            f"**캐릭터명** : {character_name}\n\n"
                            "종족을 선택하세요."
                        ),
                        color=discord.Color.blurple(),
                    )

                    await modal_inter.response.edit_message(
                        content=None,
                        embed=race_embed,
                        view=RaceView(race_callback),
                    )
                    return

                await self._process(
                    modal_inter,
                    character_name,
                    setting.default_race,
                    setting.default_server,
                    show_identity=False,
                )

            await inter.response.send_modal(
                ApplicationCharacterModal(on_character_submit)
            )

        async def cancel_callback(inter: discord.Interaction):
            current_apps = await asyncio.to_thread(
                self.service.repository.get_by_guild_raid_and_user_id,
                inter.guild.id,
                channel_raid.raid_name,
                inter.user.id,
            )

            if not current_apps:
                await inter.response.edit_message(
                    content=None,
                    embed=self._notice_embed(
                        "취소할 신청 내역이 없습니다.",
                        f"{channel_raid.raid_name}에 신청한 캐릭터가 없습니다.",
                        discord.Color.orange(),
                    ),
                    view=None,
                )
                return

            app = current_apps[0]
            ok = await asyncio.to_thread(
                self.service.cancel_application,
                app.id,
                inter.user.id,
                False,
            )

            if ok:
                cancel_embed = self.message_service.build_application_result_embed(
                    app.raid_name,
                    {
                        "character_name": app.character_name,
                        "race": app.race,
                        "server": app.server,
                        "job": app.job,
                        "item_level": app.item_level,
                        "combat_power": app.combat_power,
                    },
                    "cancelled",
                    show_identity=show_identity,
                )
                await inter.response.edit_message(
                    content=None,
                    embed=cancel_embed,
                    view=None,
                )
            else:
                await inter.response.edit_message(
                    content=None,
                    embed=self._notice_embed(
                        "신청 취소 실패",
                        "이미 취소되었거나 존재하지 않는 신청입니다.",
                        discord.Color.orange(),
                    ),
                    view=None,
                )

        async def cancel_all_callback(inter: discord.Interaction):
            current_apps = await asyncio.to_thread(
                self.service.repository.get_by_guild_raid_and_user_id,
                inter.guild.id,
                channel_raid.raid_name,
                inter.user.id,
            )

            if not current_apps:
                await inter.response.edit_message(
                    content=None,
                    embed=self._notice_embed(
                        "취소할 신청이 없습니다.",
                        "현재 레이드에 신청한 내역이 없습니다.",
                        discord.Color.orange(),
                    ),
                    view=None,
                )
                return

            count = 0
            for app in current_apps:
                ok = await asyncio.to_thread(
                    self.service.cancel_application,
                    app.id,
                    inter.user.id,
                    False,
                )
                if ok:
                    count += 1

            await inter.response.edit_message(
                content=None,
                embed=self._notice_embed(
                    "전체 취소 완료",
                    f"{count}건의 신청을 취소했습니다.",
                    discord.Color.green(),
                ),
                view=None,
            )

        async def select_cancel_callback(inter: discord.Interaction):
            current_apps = await asyncio.to_thread(
                self.service.repository.get_by_guild_raid_and_user_id,
                inter.guild.id,
                channel_raid.raid_name,
                inter.user.id,
            )

            if not current_apps:
                await inter.response.edit_message(
                    content=None,
                    embed=self._notice_embed(
                        "취소할 신청이 없습니다.",
                        "현재 레이드에 신청한 내역이 없습니다.",
                        discord.Color.orange(),
                    ),
                    view=None,
                )
                return

            selected_ids = set()

            async def refresh_view(refresh_inter, apps, ids):
                cancel_embed = self._build_cancel_select_embed(
                    applications=apps,
                    selected_ids=ids,
                    show_identity=show_identity,
                )

                view = ApplicationCancelButtonSelectView(
                    applications=apps,
                    selected_ids=ids,
                    refresh_callback=refresh_view,
                    cancel_selected_callback=cancel_selected,
                    back_callback=back_to_main,
                )

                if refresh_inter.response.is_done():
                    await refresh_inter.edit_original_response(
                        content=None,
                        embed=cancel_embed,
                        view=view,
                    )
                else:
                    await refresh_inter.response.edit_message(
                        content=None,
                        embed=cancel_embed,
                        view=view,
                    )

            async def cancel_selected(cancel_inter, ids: list[int]):
                if not ids:
                    await cancel_inter.response.send_message(
                        content=None,
                        embed=self._notice_embed(
                            "선택된 신청이 없습니다.",
                            "취소할 신청을 선택해주세요.",
                            discord.Color.orange(),
                        ),
                        ephemeral=True,
                    )
                    return

                count = 0
                for app_id in ids:
                    ok = await asyncio.to_thread(
                        self.service.cancel_application,
                        app_id,
                        cancel_inter.user.id,
                        False,
                    )
                    if ok:
                        count += 1

                await cancel_inter.response.edit_message(
                    content=None,
                    embed=self._notice_embed(
                        "신청 취소 완료",
                        f"{count}건의 신청을 취소했습니다.",
                        discord.Color.green(),
                    ),
                    view=None,
                )

            async def back_to_main(back_inter: discord.Interaction):
                await self._render_main(back_inter, first_response=False)

            await refresh_view(inter, current_apps, selected_ids)

        async def status_callback(inter: discord.Interaction):
            await self._render_status_main(
                interaction=inter,
                show_identity=show_identity,
            )

        view = ApplicationMainView(
            application_count=len(applications),
            apply_callback=apply_callback,
            cancel_callback=cancel_callback,
            select_cancel_callback=select_cancel_callback,
            cancel_all_callback=cancel_all_callback,
            status_callback=status_callback,
            admin_delete_callback=None,
        )

        if first_response:
            await interaction.response.send_message(
                content=None,
                embed=embed,
                view=view,
                ephemeral=True,
            )
        else:
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=view,
            )

    async def _get_raid_applications(self, channel_id: int):
        result = await asyncio.to_thread(
            self.service.get_current_raid_application_list,
            channel_id,
        )
        return result["raid_name"], result["applications"]

    async def _delete_applications_as_admin(
        self,
        applications,
        requester_user_id: int,
    ) -> int:
        count = 0
        for app in applications:
            ok = await asyncio.to_thread(
                self.service.cancel_application,
                app.id,
                requester_user_id,
                True,
            )
            if ok:
                count += 1
        return count

    async def _render_status_main(
        self,
        interaction: discord.Interaction,
        show_identity: bool,
    ):
        current_raid_name, applications = await self._get_raid_applications(
            interaction.channel.id
        )

        if current_raid_name is None:
            await interaction.response.edit_message(
                content=None,
                embed=self._notice_embed(
                    "레이드 신청 현황을 볼 수 없습니다.",
                    "현재 채널에 매칭된 레이드가 없습니다.",
                    discord.Color.orange(),
                ),
                view=None,
            )
            return

        embed = self._build_status_embed(
            raid_name=current_raid_name,
            applications=applications,
            show_identity=show_identity,
        )

        view = self._build_status_main_view(
            raid_name=current_raid_name,
            show_identity=show_identity,
            is_admin_user=is_admin(interaction),
        )

        if interaction.response.is_done():
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=view,
            )
        else:
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=view,
            )

    def _build_status_main_view(
        self,
        raid_name: str,
        show_identity: bool,
        is_admin_user: bool,
    ) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        command_self = self

        class UserSearchButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="유저명으로 검색",
                    style=discord.ButtonStyle.secondary,
                    row=0,
                )

            async def callback(self, interaction: discord.Interaction):
                async def submit_callback(
                    modal_inter: discord.Interaction,
                    keyword: str,
                ):
                    await command_self._render_status_search_result(
                        interaction=modal_inter,
                        keyword=keyword,
                        search_type="user",
                        show_identity=show_identity,
                    )

                await interaction.response.send_modal(
                    ApplicationStatusSearchModal(
                        title="유저명 검색",
                        submit_callback=submit_callback,
                    )
                )

        class CharacterSearchButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="캐릭터명으로 검색",
                    style=discord.ButtonStyle.secondary,
                    row=0,
                )

            async def callback(self, interaction: discord.Interaction):
                async def submit_callback(
                    modal_inter: discord.Interaction,
                    keyword: str,
                ):
                    await command_self._render_status_search_result(
                        interaction=modal_inter,
                        keyword=keyword,
                        search_type="character",
                        show_identity=show_identity,
                    )

                await interaction.response.send_modal(
                    ApplicationStatusSearchModal(
                        title="캐릭터명 검색",
                        submit_callback=submit_callback,
                    )
                )

        class DeleteAllButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="전체 삭제",
                    style=discord.ButtonStyle.danger,
                    row=0,
                )

            async def callback(self, interaction: discord.Interaction):
                if not is_admin(interaction):
                    await interaction.response.send_message(
                        "관리자만 사용할 수 있습니다.",
                        ephemeral=True,
                    )
                    return

                current_raid_name, current_apps = await command_self._get_raid_applications(
                    interaction.channel.id
                )

                count = await command_self._delete_applications_as_admin(
                    current_apps,
                    interaction.user.id,
                )

                await interaction.response.edit_message(
                    content=None,
                    embed=command_self._notice_embed(
                        "전체 삭제 완료",
                        f"{current_raid_name} 신청 내역 {count}건을 삭제했습니다.",
                        discord.Color.green(),
                    ),
                    view=None,
                )

        class BackButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="뒤로 가기",
                    style=discord.ButtonStyle.secondary,
                    row=0,
                )

            async def callback(self, interaction: discord.Interaction):
                await command_self._render_main(interaction, first_response=False)

        view.add_item(UserSearchButton())
        view.add_item(CharacterSearchButton())

        if is_admin_user:
            view.add_item(DeleteAllButton())

        view.add_item(BackButton())
        return view

    async def _render_status_search_result(
        self,
        interaction: discord.Interaction,
        keyword: str,
        search_type: str,
        show_identity: bool,
    ):
        current_raid_name, applications = await self._get_raid_applications(
            interaction.channel.id
        )

        if search_type == "user":
            filtered = [
                app for app in applications
                if keyword.lower() in str(app.user_name).lower()
            ]
            label = "유저명 검색"
        else:
            filtered = [
                app for app in applications
                if keyword.lower() in str(app.character_name).lower()
            ]
            label = "캐릭터명 검색"

        embed = self._build_status_embed(
            raid_name=current_raid_name,
            applications=filtered,
            show_identity=show_identity,
            keyword=keyword,
            search_label=label,
        )

        view = self._build_status_search_result_view(
            raid_name=current_raid_name,
            applications=filtered,
            show_identity=show_identity,
            keyword=keyword,
            search_type=search_type,
            is_admin_user=is_admin(interaction),
        )

        if interaction.response.is_done():
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=view,
            )
        else:
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=view,
            )

    def _build_status_search_result_view(
        self,
        raid_name: str,
        applications,
        show_identity: bool,
        keyword: str,
        search_type: str,
        is_admin_user: bool,
    ) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        command_self = self

        class DeleteOneButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="신청 삭제",
                    style=discord.ButtonStyle.danger,
                    row=0,
                )

            async def callback(self, interaction: discord.Interaction):
                if not is_admin(interaction):
                    await interaction.response.send_message(
                        "관리자만 사용할 수 있습니다.",
                        ephemeral=True,
                    )
                    return

                app = applications[0]
                ok = await asyncio.to_thread(
                    command_self.service.cancel_application,
                    app.id,
                    interaction.user.id,
                    True,
                )

                if ok:
                    await interaction.response.edit_message(
                        content=None,
                        embed=command_self._notice_embed(
                            "신청 삭제 완료",
                            f"{app.character_name} 신청 내역을 삭제했습니다.",
                            discord.Color.green(),
                        ),
                        view=None,
                    )
                else:
                    await interaction.response.edit_message(
                        content=None,
                        embed=command_self._notice_embed(
                            "신청 삭제 실패",
                            "이미 삭제되었거나 존재하지 않는 신청입니다.",
                            discord.Color.orange(),
                        ),
                        view=None,
                    )

        class SelectDeleteButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="선택 삭제",
                    style=discord.ButtonStyle.danger,
                    row=0,
                )

            async def callback(self, interaction: discord.Interaction):
                if not is_admin(interaction):
                    await interaction.response.send_message(
                        "관리자만 사용할 수 있습니다.",
                        ephemeral=True,
                    )
                    return

                await command_self._render_status_delete_select(
                    interaction=interaction,
                    applications=applications,
                    show_identity=show_identity,
                    keyword=keyword,
                    search_type=search_type,
                )

        class DeleteAllResultButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="전체 삭제",
                    style=discord.ButtonStyle.danger,
                    row=0,
                )

            async def callback(self, interaction: discord.Interaction):
                if not is_admin(interaction):
                    await interaction.response.send_message(
                        "관리자만 사용할 수 있습니다.",
                        ephemeral=True,
                    )
                    return

                count = await command_self._delete_applications_as_admin(
                    applications,
                    interaction.user.id,
                )

                await interaction.response.edit_message(
                    content=None,
                    embed=command_self._notice_embed(
                        "전체 삭제 완료",
                        f"검색 결과 신청 내역 {count}건을 삭제했습니다.",
                        discord.Color.green(),
                    ),
                    view=None,
                )

        class BackButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="뒤로 가기",
                    style=discord.ButtonStyle.secondary,
                    row=0,
                )

            async def callback(self, interaction: discord.Interaction):
                await command_self._render_status_main(
                    interaction=interaction,
                    show_identity=show_identity,
                )

        if is_admin_user and applications:
            if len(applications) == 1:
                view.add_item(DeleteOneButton())
            else:
                view.add_item(SelectDeleteButton())
                view.add_item(DeleteAllResultButton())

        view.add_item(BackButton())
        return view

    async def _render_status_delete_select(
        self,
        interaction: discord.Interaction,
        applications,
        show_identity: bool,
        keyword: str,
        search_type: str,
    ):
        selected_ids = set()

        async def refresh_view(refresh_inter, apps, ids):
            embed = self._build_admin_delete_select_embed(
                applications=apps,
                selected_ids=ids,
                show_identity=show_identity,
            )

            view = self._build_admin_delete_select_view(
                applications=apps,
                selected_ids=ids,
                refresh_callback=refresh_view,
                delete_selected_callback=delete_selected,
                back_callback=back_to_result,
            )

            if refresh_inter.response.is_done():
                await refresh_inter.edit_original_response(
                    content=None,
                    embed=embed,
                    view=view,
                )
            else:
                await refresh_inter.response.edit_message(
                    content=None,
                    embed=embed,
                    view=view,
                )

        async def delete_selected(delete_inter, ids: list[int]):
            if not ids:
                await delete_inter.response.send_message(
                    "삭제할 신청을 선택해주세요.",
                    ephemeral=True,
                )
                return

            targets = [app for app in applications if app.id in ids]
            count = await self._delete_applications_as_admin(
                targets,
                delete_inter.user.id,
            )

            await delete_inter.response.edit_message(
                content=None,
                embed=self._notice_embed(
                    "선택 삭제 완료",
                    f"선택한 신청 내역 {count}건을 삭제했습니다.",
                    discord.Color.green(),
                ),
                view=None,
            )

        async def back_to_result(back_inter):
            await self._render_status_search_result(
                interaction=back_inter,
                keyword=keyword,
                search_type=search_type,
                show_identity=show_identity,
            )

        await refresh_view(interaction, applications, selected_ids)

    def _build_admin_delete_select_embed(
        self,
        applications,
        selected_ids,
        show_identity: bool,
    ) -> discord.Embed:
        lines = []

        for idx, app in enumerate(applications, start=1):
            mark = "✅" if app.id in selected_ids else "⬜"
            line = self._format_application_line(
                idx=idx,
                app=app,
                show_identity=show_identity,
                include_user_name=True,
            )
            line = line.replace(f"{idx}. ", f"{mark} {idx}. ", 1)

            if app.id in selected_ids:
                line = f"**{line}**"

            lines.append(line)

        return discord.Embed(
            title="삭제할 신청 선택",
            description="\n".join(lines) if lines else "삭제할 신청 내역이 없습니다.",
            color=discord.Color.orange(),
        )

    def _build_admin_delete_select_view(
        self,
        applications,
        selected_ids,
        refresh_callback,
        delete_selected_callback,
        back_callback,
    ) -> discord.ui.View:
        view = discord.ui.View(timeout=180)

        class ToggleButton(discord.ui.Button):
            def __init__(self, idx: int, app):
                selected = app.id in selected_ids
                super().__init__(
                    label=str(idx),
                    style=discord.ButtonStyle.success if selected else discord.ButtonStyle.secondary,
                    row=0 if idx <= 5 else 1,
                )
                self.app = app

            async def callback(self, interaction: discord.Interaction):
                if self.app.id in selected_ids:
                    selected_ids.remove(self.app.id)
                else:
                    selected_ids.add(self.app.id)

                await refresh_callback(interaction, applications, selected_ids)

        class DeleteSelectedButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="선택 삭제",
                    style=discord.ButtonStyle.danger,
                    row=2,
                )

            async def callback(self, interaction: discord.Interaction):
                await delete_selected_callback(interaction, list(selected_ids))

        class BackButton(discord.ui.Button):
            def __init__(self):
                super().__init__(
                    label="뒤로 가기",
                    style=discord.ButtonStyle.secondary,
                    row=2,
                )

            async def callback(self, interaction: discord.Interaction):
                await back_callback(interaction)

        for idx, app in enumerate(applications[:8], start=1):
            view.add_item(ToggleButton(idx, app))

        view.add_item(DeleteSelectedButton())
        view.add_item(BackButton())

        return view

    @app_commands.command(name="신청", description="레이드 신청 메뉴")
    async def apply(self, interaction: discord.Interaction):
        try:
            await self._render_main(interaction, first_response=True)
        except Exception as exc:
            await self._respond_error(interaction, exc)

    async def _process(
        self,
        interaction,
        character_name,
        race,
        server,
        show_identity: bool,
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            if interaction.guild is None or interaction.channel is None:
                await interaction.edit_original_response(
                    content=None,
                    embed=self._error_embed(
                        "사용할 수 없는 위치입니다.",
                        "서버 채널에서만 사용할 수 있습니다.",
                    ),
                    view=None,
                )
                return

            guild_display_name = interaction.user.display_name

            result = await asyncio.to_thread(
                self.service.process,
                interaction.guild.id,
                interaction.channel.id,
                interaction.user.id,
                guild_display_name,
                character_name,
                race,
                server,
            )

            print(
                "[APPLICATION]",
                f"guild_id={interaction.guild.id}",
                f"channel_id={interaction.channel.id}",
                f"user_id={interaction.user.id}",
                f"character_name={character_name}",
                f"action={result.get('action')}",
            )

            if result["action"] == "created":
                embed = self.message_service.build_application_result_embed(
                    result["raid_name"],
                    result["info"],
                    "created",
                    show_identity=show_identity,
                )

                added_to_waiting = await asyncio.to_thread(
                    self.service.register_to_waiting_if_party_exists,
                    interaction.guild.id,
                    interaction.channel.id,
                    result["application"],
                    self.party_manage_service,
                    self.party_waiting_repository,
                )

                sent_to_channel = False
                send_fail_reason = None

                if interaction.channel is not None:
                    try:
                        await interaction.channel.send(embed=embed)
                        sent_to_channel = True
                    except discord.Forbidden:
                        send_fail_reason = "봇에게 현재 채널 메시지 전송 권한이 없습니다."
                    except discord.HTTPException as exc:
                        send_fail_reason = f"디스코드 전송 오류가 발생했습니다. 상태 코드: {exc.status}"
                    except Exception as exc:
                        send_fail_reason = f"알 수 없는 전송 오류가 발생했습니다. ({type(exc).__name__})"

                if added_to_waiting:
                    embed.add_field(
                        name="추가 안내",
                        value="이미 공대가 생성된 상태라 상비군으로도 등록되었습니다.",
                        inline=False,
                    )

                if sent_to_channel:
                    embed.add_field(
                        name="처리 결과",
                        value="공개 채널에 신청 완료 메시지를 전송했습니다.",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="공개 메시지 전송 실패",
                        value=send_fail_reason or "채널에 공개 메시지를 전송하지 못했습니다.",
                        inline=False,
                    )

                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=None,
                )

            elif result["action"] == "show_current":
                embed = self.message_service.build_application_result_embed(
                    result["raid_name"],
                    result["info"],
                    result["action"],
                    show_identity=show_identity,
                )
                view = ApplicationResultView(
                    application_service=self.service,
                    application_id=result["application"].id,
                    owner_user_id=interaction.user.id,
                )
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=view,
                )

            elif result["action"] == "already_exists_other_user":
                embed = self.message_service.build_application_result_embed(
                    result["raid_name"],
                    result["info"],
                    result["action"],
                    show_identity=show_identity,
                )

                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=None,
                )

            elif result["action"] == "show_all":
                embed = self.message_service.build_application_all_embed(
                    result["info"],
                    result["applications"],
                    show_identity=show_identity,
                )
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=None,
                )

            elif result["action"] == "rejected":
                embed = self.message_service.build_application_result_embed(
                    result["raid_name"],
                    result["info"],
                    result["action"],
                    show_identity=show_identity,
                )

                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=None,
                )

            elif result["action"] == "not_allowed":
                await interaction.edit_original_response(
                    content=None,
                    embed=self._notice_embed(
                        "신청할 수 없습니다.",
                        result.get("message", "현재 채널에서는 신청할 수 없습니다."),
                        discord.Color.orange(),
                    ),
                    view=None,
                )

            else:
                await interaction.edit_original_response(
                    content=None,
                    embed=self._notice_embed(
                        "처리 결과",
                        result.get("message", "요청 처리가 완료되었습니다."),
                        discord.Color.orange(),
                    ),
                    view=None,
                )

        except Exception as exc:
            print(
                "[APPLICATION][PROCESS_ERROR]",
                f"guild_id={getattr(interaction.guild, 'id', None)}",
                f"channel_id={getattr(interaction.channel, 'id', None)}",
                f"character_name={character_name}",
                repr(exc),
            )
            await interaction.edit_original_response(
                content=None,
                embed=self._error_embed(
                    "신청 처리 중 오류가 발생했습니다.",
                    self._friendly_error_message(exc),
                ),
                view=None,
            )
