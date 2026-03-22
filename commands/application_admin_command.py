import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils.permissions import ensure_guild_only, is_admin
from views.application_admin_view import (
    AdminApplicationAddModal,
    AdminApplicationDeleteCharacterModal,
    AdminApplicationDeleteManageView,
    AdminApplicationUserSearchModal,
    AdminApplicationUserResultView,
    ApplicationAdminDeleteModeView,
    ApplicationAdminMainView,
)
from views.application_view import RaceView, ServerView


class ApplicationAdminCommand(commands.Cog):
    def __init__(self, bot, application_service, setting_service, raid_service, message_service):
        self.bot = bot
        self.application_service = application_service
        self.setting_service = setting_service
        self.raid_service = raid_service
        self.message_service = message_service

    @app_commands.command(name="신청관리", description="관리자용 신청 관리")
    async def application_admin(self, interaction: discord.Interaction):
        if not ensure_guild_only(interaction):
            await interaction.response.send_message(
                "서버 채널에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        if not is_admin(interaction):
            await interaction.response.send_message(
                "관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "서버 채널에서만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        channel_raid = self.raid_service.get_channel_raid(interaction.channel.id)
        if channel_raid is None:
            await interaction.response.send_message(
                "현재 채널에 레이드가 설정되어 있지 않습니다.",
                ephemeral=True,
            )
            return

        async def add_callback(inter: discord.Interaction):
            async def on_add_submit(
                submit_inter: discord.Interaction,
                raw_target_user: str,
                character_name: str,
            ):
                if submit_inter.guild is None:
                    await submit_inter.response.send_message(
                        "서버 채널에서만 사용할 수 있습니다.",
                        ephemeral=True,
                    )
                    return

                selected_user = self._resolve_member_from_input(
                    submit_inter.guild,
                    raw_target_user,
                )

                if selected_user is None or selected_user.bot:
                    await submit_inter.response.send_message(
                        "대상 유저를 찾을 수 없습니다. 멘션 또는 유저 ID를 확인해 주세요.",
                        ephemeral=True,
                    )
                    return

                setting = self.setting_service.get_guild_setting(submit_inter.guild.id)

                if not setting:
                    async def race_callback(race_inter: discord.Interaction, race: str):
                        await race_inter.response.edit_message(
                            content=f"종족: **{race}**\n서버를 선택하세요.",
                            view=ServerView(
                                race,
                                lambda i, r, s: self._admin_create_application(
                                    i,
                                    selected_user,
                                    character_name,
                                    r,
                                    s,
                                    show_identity=True,
                                ),
                            ),
                            embed=None,
                        )

                    await submit_inter.response.send_message(
                        content="기본 서버 설정이 없습니다.\n종족을 선택하세요.",
                        view=RaceView(race_callback),
                        ephemeral=True,
                    )
                    return

                await self._admin_create_application(
                    submit_inter,
                    selected_user,
                    character_name,
                    setting.default_race,
                    setting.default_server,
                    show_identity=False,
                )

            await inter.response.send_modal(
                AdminApplicationAddModal(on_add_submit)
            )

        async def list_callback(inter: discord.Interaction):
            result = await asyncio.to_thread(
                self.application_service.get_current_raid_application_list,
                inter.channel.id,
            )

            setting = self.setting_service.get_guild_setting(inter.guild.id)
            show_identity = not bool(
                setting and setting.default_race and setting.default_server
            )

            embed = self.message_service.build_admin_application_list_embed(
                result["raid_name"],
                result["applications"],
                show_identity=show_identity,
            )

            await inter.response.edit_message(
                content=None,
                embed=embed,
                view=None,
            )

        async def delete_callback(inter: discord.Interaction):
            async def back_callback(back_inter: discord.Interaction):
                await back_inter.response.edit_message(
                    content="신청 관리 항목을 선택하세요.",
                    view=ApplicationAdminMainView(
                        add_callback=add_callback,
                        list_callback=list_callback,
                        delete_callback=delete_callback,
                    ),
                    embed=None,
                )

            async def by_user_callback(user_inter: discord.Interaction):
                async def on_user_search(submit_inter: discord.Interaction, keyword: str):
                    if submit_inter.guild is None:
                        await submit_inter.response.send_message(
                            "서버 채널에서만 사용할 수 있습니다.",
                            ephemeral=True,
                        )
                        return

                    members = await self._search_guild_members(submit_inter.guild, keyword)

                    if not members:
                        await submit_inter.response.send_message(
                            "검색 결과가 없습니다.",
                            ephemeral=True,
                        )
                        return

                    async def on_user_selected(select_inter: discord.Interaction, selected_user: discord.Member):
                        result = await asyncio.to_thread(
                            self.application_service.search_current_raid_applications_by_user,
                            select_inter.channel.id,
                            selected_user.id,
                        )

                        applications = result["applications"]
                        selected_ids = set()

                        async def refresh_manage_view(refresh_inter: discord.Interaction, apps, ids):
                            setting = self.setting_service.get_guild_setting(refresh_inter.guild.id)
                            show_identity = not bool(
                                setting and setting.default_race and setting.default_server
                            )

                            embed = self.message_service.build_admin_delete_search_embed(
                                "삭제 대상 선택",
                                apps,
                                show_identity=show_identity,
                            )
                            view = AdminApplicationDeleteManageView(
                                applications=apps,
                                selected_ids=ids,
                                refresh_callback=refresh_manage_view,
                                delete_callback=delete_selected,
                                allow_select_all=True,
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

                        async def delete_selected(delete_inter: discord.Interaction, ids: list[int]):
                            deleted_count = await asyncio.to_thread(
                                self.application_service.admin_delete_applications,
                                ids,
                            )
                            await delete_inter.response.edit_message(
                                content=f"신청 {deleted_count}건을 강제 삭제했습니다.",
                                embed=None,
                                view=None,
                            )

                        await refresh_manage_view(select_inter, applications, selected_ids)

                    await submit_inter.response.send_message(
                        content="검색 결과입니다. 삭제할 유저를 선택하세요.",
                        view=AdminApplicationUserResultView(members, on_user_selected),
                        ephemeral=True,
                    )

                await user_inter.response.send_modal(
                    AdminApplicationUserSearchModal(on_user_search)
                )

            async def by_character_callback(char_inter: discord.Interaction):
                async def on_character_submit(modal_inter: discord.Interaction, character_name: str):
                    result = await asyncio.to_thread(
                        self.application_service.search_current_raid_applications_by_character,
                        modal_inter.channel.id,
                        character_name,
                    )

                    applications = result["applications"]
                    selected_ids = set()

                    async def refresh_manage_view(refresh_inter: discord.Interaction, apps, ids):
                        setting = self.setting_service.get_guild_setting(refresh_inter.guild.id)
                        show_identity = not bool(
                            setting and setting.default_race and setting.default_server
                        )

                        embed = self.message_service.build_admin_delete_search_embed(
                            "삭제 대상 선택",
                            apps,
                            show_identity=show_identity,
                        )
                        view = AdminApplicationDeleteManageView(
                            applications=apps,
                            selected_ids=ids,
                            refresh_callback=refresh_manage_view,
                            delete_callback=delete_selected,
                            allow_select_all=False,
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

                    async def delete_selected(delete_inter: discord.Interaction, ids: list[int]):
                        deleted_count = await asyncio.to_thread(
                            self.application_service.admin_delete_applications,
                            ids,
                        )
                        await delete_inter.response.edit_message(
                            content=f"신청 {deleted_count}건을 강제 삭제했습니다.",
                            embed=None,
                            view=None,
                        )

                    await refresh_manage_view(modal_inter, applications, selected_ids)

                await char_inter.response.send_modal(
                    AdminApplicationDeleteCharacterModal(on_character_submit)
                )

            await inter.response.edit_message(
                content="삭제 방식을 선택하세요.",
                view=ApplicationAdminDeleteModeView(
                    by_user_callback=by_user_callback,
                    by_character_callback=by_character_callback,
                    back_callback=back_callback,
                ),
                embed=None,
            )

        await interaction.response.send_message(
            content="신청 관리 항목을 선택하세요.",
            view=ApplicationAdminMainView(
                add_callback=add_callback,
                list_callback=list_callback,
                delete_callback=delete_callback,
            ),
            ephemeral=True,
        )

    async def _admin_create_application(
        self,
        interaction: discord.Interaction,
        selected_user: discord.Member,
        character_name: str,
        race: str,
        server: str,
        show_identity: bool,
    ):
        await interaction.response.defer(ephemeral=True)

        guild_display_name = self._resolve_guild_display_name(
            interaction.guild,
            selected_user,
        )

        result = await asyncio.to_thread(
            self.application_service.admin_create_application,
            interaction.guild.id,
            interaction.channel.id,
            selected_user.id,
            guild_display_name,
            character_name,
            race,
            server,
        )

        if result["action"] == "created":
            embed = self.message_service.build_application_result_embed(
                result["raid_name"],
                result["info"],
                "created",
                show_identity=show_identity,
            )

            if interaction.channel is not None:
                try:
                    await interaction.channel.send(embed=embed)
                except discord.Forbidden:
                    pass

            await interaction.edit_original_response(
                content=f"{result['raid_name']} 신청이 추가되었습니다.",
                embed=None,
                view=None,
            )
            return

        if result["action"] == "show_current":
            embed = self.message_service.build_admin_application_created_embed(
                result["raid_name"],
                guild_display_name,
                result["info"],
                show_identity=show_identity,
            )
            await interaction.edit_original_response(
                content=f"{result['raid_name']} 신청 내역이 이미 있어 최신 정보로 갱신되었습니다.",
                embed=embed,
                view=None,
            )
            return

        await interaction.edit_original_response(
            content=result["message"],
            embed=None,
            view=None,
        )

    async def _search_guild_members(
        self,
        guild: discord.Guild,
        keyword: str,
    ) -> list[discord.Member]:
        keyword_lower = keyword.lower()
        members: list[discord.Member] = []

        async for member in guild.fetch_members(limit=None):
            if member.bot:
                continue

            display_name = (member.display_name or "").lower()
            username = (member.name or "").lower()

            if keyword_lower in display_name or keyword_lower in username:
                members.append(member)

        return members[:25]

    def _resolve_member_from_input(
        self,
        guild: discord.Guild,
        raw_value: str,
    ) -> discord.Member | None:
        value = raw_value.strip()

        if value.startswith("<@") and value.endswith(">"):
            value = value.replace("<@", "").replace("!", "").replace(">", "").strip()

        if value.isdigit():
            return guild.get_member(int(value))

        return None

    def _resolve_guild_display_name(self, guild: discord.Guild, selected_user: discord.Member) -> str:
        member = guild.get_member(selected_user.id)
        if member is not None:
            return member.display_name
        return selected_user.display_name
