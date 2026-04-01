import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils.permissions import ensure_guild_only, is_admin
from views.application_admin_view import (
    AdminApplicationDeleteCharacterModal,
    AdminApplicationUserSearchModal,
    ApplicationAdminDeleteModeView,
    ApplicationAdminListView,
    ApplicationAdminMainView,
    ApplicationAdminUserSearchResultView,
    MultiDeleteView,
    SingleDeleteView,
)


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

        async def go_main(inter: discord.Interaction):
            await inter.response.edit_message(
                content="신청 관리 항목을 선택하세요.",
                embed=None,
                view=ApplicationAdminMainView(
                    list_callback=list_callback,
                    delete_callback=delete_callback,
                ),
            )

        async def go_delete_mode(inter: discord.Interaction):
            await inter.response.edit_message(
                content="삭제 방법을 선택하세요.",
                embed=None,
                view=ApplicationAdminDeleteModeView(
                    by_user_callback=by_user_callback,
                    by_character_callback=by_character_callback,
                    back_callback=go_main,
                ),
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
                content="신청내역",
                embed=embed,
                view=ApplicationAdminListView(back_callback=go_main),
            )

        async def render_user_applications_delete_view(
            inter: discord.Interaction,
            applications,
            back_callback,
        ):
            setting = self.setting_service.get_guild_setting(inter.guild.id)
            show_identity = not bool(
                setting and setting.default_race and setting.default_server
            )

            selected_ids = set()

            async def refresh_manage_view(refresh_inter: discord.Interaction, apps, ids):
                embed = self.message_service.build_admin_delete_search_embed(
                    "삭제 대상 선택",
                    apps,
                    show_identity=show_identity,
                )
                view = MultiDeleteView(
                    applications=apps,
                    selected_ids=ids,
                    refresh_callback=refresh_manage_view,
                    delete_selected_callback=delete_selected,
                    delete_all_callback=delete_all,
                    back_callback=back_callback,
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

            async def delete_all(delete_inter: discord.Interaction):
                ids = [app.id for app in applications if app.id is not None]
                deleted_count = await asyncio.to_thread(
                    self.application_service.admin_delete_applications,
                    ids,
                )
                await delete_inter.response.edit_message(
                    content=f"신청 {deleted_count}건을 강제 삭제했습니다.",
                    embed=None,
                    view=None,
                )

            await refresh_manage_view(inter, applications, selected_ids)

        async def by_user_callback(inter: discord.Interaction):
            async def on_user_search(modal_inter: discord.Interaction, keyword: str):
                result = await asyncio.to_thread(
                    self.application_service.search_current_raid_users,
                    modal_inter.channel.id,
                    keyword,
                )

                users = result["users"]
                if not users:
                    await modal_inter.response.edit_message(
                        content="검색 결과가 없습니다.",
                        embed=None,
                        view=None,
                    )
                    return

                async def back_to_delete_mode(back_inter: discord.Interaction):
                    await back_inter.response.edit_message(
                        content="삭제 방법을 선택하세요.",
                        embed=None,
                        view=ApplicationAdminDeleteModeView(
                            by_user_callback=by_user_callback,
                            by_character_callback=by_character_callback,
                            back_callback=go_main,
                        ),
                    )

                async def on_user_selected(select_inter: discord.Interaction, selected_user: dict):
                    result = await asyncio.to_thread(
                        self.application_service.search_current_raid_applications_by_user,
                        select_inter.channel.id,
                        selected_user["user_id"],
                    )

                    applications = result["applications"]
                    await render_user_applications_delete_view(
                        select_inter,
                        applications,
                        back_callback=back_to_delete_mode,
                    )

                if len(users) == 1:
                    result = await asyncio.to_thread(
                        self.application_service.search_current_raid_applications_by_user,
                        modal_inter.channel.id,
                        users[0]["user_id"],
                    )

                    await render_user_applications_delete_view(
                        modal_inter,
                        result["applications"],
                        back_callback=back_to_delete_mode,
                    )
                    return

                setting = self.setting_service.get_guild_setting(modal_inter.guild.id)
                show_identity = not bool(
                    setting and setting.default_race and setting.default_server
                )

                embed = self.message_service.build_admin_user_search_result_embed(
                    "유저 검색 결과",
                    users,
                )

                await modal_inter.response.edit_message(
                    content=None,
                    embed=embed,
                    view=ApplicationAdminUserSearchResultView(
                        users=users,
                        select_callback=on_user_selected,
                        back_callback=back_to_delete_mode,
                    ),
                )

            await inter.response.send_modal(
                AdminApplicationUserSearchModal(on_user_search)
            )

        async def by_character_callback(inter: discord.Interaction):
            async def on_character_submit(modal_inter: discord.Interaction, character_name: str):
                result = await asyncio.to_thread(
                    self.application_service.search_current_raid_applications_by_character,
                    modal_inter.channel.id,
                    character_name,
                )

                applications = result["applications"]
                if not applications:
                    await modal_inter.response.edit_message(
                        content="검색 결과가 없습니다.",
                        embed=None,
                        view=None,
                    )
                    return

                setting = self.setting_service.get_guild_setting(modal_inter.guild.id)
                show_identity = not bool(
                    setting and setting.default_race and setting.default_server
                )

                async def back_to_delete_mode(back_inter: discord.Interaction):
                    await back_inter.response.edit_message(
                        content="삭제 방법을 선택하세요.",
                        embed=None,
                        view=ApplicationAdminDeleteModeView(
                            by_user_callback=by_user_callback,
                            by_character_callback=by_character_callback,
                            back_callback=go_main,
                        ),
                    )

                if len(applications) == 1:
                    application = applications[0]

                    embed = self.message_service.build_admin_delete_search_embed(
                        "삭제 확인",
                        [application],
                        show_identity=show_identity,
                    )

                    async def single_delete(delete_inter: discord.Interaction):
                        deleted_count = await asyncio.to_thread(
                            self.application_service.admin_delete_applications,
                            [application.id],
                        )
                        await delete_inter.response.edit_message(
                            content=f"신청 {deleted_count}건을 강제 삭제했습니다.",
                            embed=None,
                            view=None,
                        )

                    await modal_inter.response.edit_message(
                        content=None,
                        embed=embed,
                        view=SingleDeleteView(
                            delete_callback=single_delete,
                            back_callback=back_to_delete_mode,
                        ),
                    )
                    return

                selected_ids = set()

                async def refresh_manage_view(refresh_inter: discord.Interaction, apps, ids):
                    embed = self.message_service.build_admin_delete_search_embed(
                        "삭제 대상 선택",
                        apps,
                        show_identity=show_identity,
                    )
                    view = MultiDeleteView(
                        applications=apps,
                        selected_ids=ids,
                        refresh_callback=refresh_manage_view,
                        delete_selected_callback=delete_selected,
                        delete_all_callback=delete_all,
                        back_callback=back_to_delete_mode,
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

                async def delete_all(delete_inter: discord.Interaction):
                    ids = [app.id for app in applications if app.id is not None]
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

            await inter.response.send_modal(
                AdminApplicationDeleteCharacterModal(on_character_submit)
            )

        await interaction.response.send_message(
            content="신청 관리 항목을 선택하세요.",
            view=ApplicationAdminMainView(
                list_callback=list_callback,
                delete_callback=delete_callback,
            ),
            ephemeral=True,
        )
