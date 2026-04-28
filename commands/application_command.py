import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils.permissions import is_admin

from views.application_view import RaceView, ServerView
from views.application_result_view import ApplicationResultView
from views.application_main_view import ApplicationMainView, ApplicationCharacterModal
from views.application_cancel_view import ApplicationCancelSelectView


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

    @app_commands.command(name="신청", description="레이드 신청 메뉴")
    async def apply(self, interaction: discord.Interaction):
        try:
            if interaction.guild is None or interaction.channel is None:
                await interaction.response.send_message(
                    "서버 채널에서만 사용할 수 있습니다.",
                    ephemeral=True,
                )
                return

            channel_raid = self.service.raid_service.get_channel_raid(
                interaction.channel.id
            )

            if channel_raid is not None:
                applications = await asyncio.to_thread(
                    self.service.repository.get_by_guild_raid_and_user_id,
                    interaction.guild.id,
                    channel_raid.raid_name,
                    interaction.user.id,
                )
                title = f"내 {channel_raid.raid_name} 신청 현황"
                content = f"{channel_raid.raid_name} 신청 메뉴입니다."
            else:
                applications = await asyncio.to_thread(
                    self.service.repository.get_by_guild_and_user_id,
                    interaction.guild.id,
                    interaction.user.id,
                )
                title = "내 전체 신청 현황"
                content = "현재 채널에 매칭된 레이드가 없습니다."

            if applications:
                lines = []
                for idx, app in enumerate(applications, start=1):
                    lines.append(
                        f"{idx}. **{app.raid_name}** | "
                        f"{app.character_name} | {app.job} | "
                        f"{app.item_level} | {app.combat_power:,}"
                    )

                embed = discord.Embed(
                    title=title,
                    description="\n".join(lines),
                )
            else:
                embed = discord.Embed(
                    title=title,
                    description="신청 내역이 없습니다.",
                )

            if channel_raid is None:
                await interaction.response.send_message(
                    content=content,
                    embed=embed,
                    ephemeral=True,
                )
                return

            async def apply_callback(inter: discord.Interaction):
                async def on_character_submit(
                    modal_inter: discord.Interaction,
                    character_name: str,
                ):
                    setting = self.setting_service.get_guild_setting(
                        modal_inter.guild.id
                    )

                    if not setting:
                        async def race_callback(race_inter, race):
                            await race_inter.response.edit_message(
                                content=f"종족: **{race}**\n서버를 선택하세요.",
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
                                embed=None,
                            )

                        await modal_inter.response.send_message(
                            content="기본 서버 설정이 없습니다.\n종족을 선택하세요.",
                            view=RaceView(race_callback),
                            ephemeral=True,
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
                applications = await asyncio.to_thread(
                    self.service.repository.get_by_guild_raid_and_user_id,
                    inter.guild.id,
                    channel_raid.raid_name,
                    inter.user.id,
                )

                if not applications:
                    await inter.response.edit_message(
                        content="취소할 신청 내역이 없습니다.",
                        embed=None,
                        view=None,
                    )
                    return

                if len(applications) == 1:
                    app = applications[0]
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
                            show_identity=True,
                        )
                        await inter.response.edit_message(
                            content=None,
                            embed=cancel_embed,
                            view=None,
                        )
                    else:
                        await inter.response.edit_message(
                            content="이미 취소되었거나 존재하지 않는 신청입니다.",
                            embed=None,
                            view=None,
                        )
                    return

                selected_ids = set()

                async def refresh_cancel_view(refresh_inter, apps, ids):
                    lines = []
                    for idx, app in enumerate(apps, start=1):
                        checked = "✅" if app.id in ids else "⬜"
                        lines.append(
                            f"{checked} {idx}. **{app.raid_name}** | "
                            f"{app.character_name} | {app.job} | "
                            f"{app.item_level} | {app.combat_power:,}"
                        )

                    cancel_list_embed = discord.Embed(
                        title="신청 취소 대상 선택",
                        description="\n".join(lines),
                    )

                    view = ApplicationCancelSelectView(
                        applications=apps,
                        selected_ids=ids,
                        refresh_callback=refresh_cancel_view,
                        cancel_selected_callback=cancel_selected,
                        cancel_all_callback=cancel_all,
                    )

                    if refresh_inter.response.is_done():
                        await refresh_inter.edit_original_response(
                            content=None,
                            embed=cancel_list_embed,
                            view=view,
                        )
                    else:
                        await refresh_inter.response.edit_message(
                            content=None,
                            embed=cancel_list_embed,
                            view=view,
                        )

                async def cancel_selected(cancel_inter, ids: list[int]):
                    if not ids:
                        await cancel_inter.response.send_message(
                            "취소할 신청을 선택하세요.",
                            ephemeral=True,
                        )
                        return

                    cancelled_count = 0
                    for application_id in ids:
                        ok = await asyncio.to_thread(
                            self.service.cancel_application,
                            application_id,
                            cancel_inter.user.id,
                            False,
                        )
                        if ok:
                            cancelled_count += 1

                    await cancel_inter.response.edit_message(
                        content=f"신청 {cancelled_count}건을 취소했습니다.",
                        embed=None,
                        view=None,
                    )

                async def cancel_all(cancel_inter):
                    cancelled_count = 0
                    for app in applications:
                        ok = await asyncio.to_thread(
                            self.service.cancel_application,
                            app.id,
                            cancel_inter.user.id,
                            False,
                        )
                        if ok:
                            cancelled_count += 1

                    await cancel_inter.response.edit_message(
                        content=f"신청 {cancelled_count}건을 취소했습니다.",
                        embed=None,
                        view=None,
                    )

                await refresh_cancel_view(inter, applications, selected_ids)

            async def status_callback(inter: discord.Interaction):
                result = await asyncio.to_thread(
                    self.service.get_current_raid_application_list,
                    inter.channel.id,
                )

                if result["raid_name"] is None:
                    await inter.response.edit_message(
                        content="현재 채널에 매칭된 레이드가 없습니다.",
                        embed=None,
                        view=None,
                    )
                    return

                setting = self.setting_service.get_guild_setting(inter.guild.id)
                show_identity = not bool(
                    setting and setting.default_race and setting.default_server
                )

                status_embed = self.message_service.build_admin_application_list_embed(
                    result["raid_name"],
                    result["applications"],
                    show_identity=show_identity,
                )

                await inter.response.edit_message(
                    content=f"{result['raid_name']} 신청자 목록",
                    embed=status_embed,
                    view=None,
                )

            admin_delete_callback = None
            if is_admin(interaction):
                async def admin_delete_callback(inter: discord.Interaction):
                    await inter.response.edit_message(
                        content="관리자 삭제 기능은 다음 단계에서 연결됩니다.",
                        embed=None,
                        view=None,
                    )

            await interaction.response.send_message(
                content=content,
                embed=embed,
                view=ApplicationMainView(
                    apply_callback=apply_callback,
                    cancel_callback=cancel_callback,
                    status_callback=status_callback,
                    admin_delete_callback=admin_delete_callback,
                ),
                ephemeral=True,
            )

        except Exception as exc:
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content=f"오류가 발생했습니다: {exc}",
                    embed=None,
                    view=None,
                )
            else:
                await interaction.response.send_message(
                    f"오류가 발생했습니다: {exc}",
                    ephemeral=True,
                )

    async def _process(self, interaction, character_name, race, server, show_identity: bool):
        await interaction.response.defer(ephemeral=True)

        try:
            if interaction.guild is None or interaction.channel is None:
                await interaction.edit_original_response(
                    content="서버 채널에서만 사용할 수 있습니다.",
                    embed=None,
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
                        send_fail_reason = "채널 전송 권한이 없습니다."
                    except discord.HTTPException as exc:
                        send_fail_reason = f"채널 전송 중 HTTP 오류가 발생했습니다. ({exc.status})"
                    except Exception as exc:
                        send_fail_reason = f"채널 전송 중 알 수 없는 오류가 발생했습니다. ({type(exc).__name__})"

                complete_message = "신청이 완료되었습니다."
                if added_to_waiting:
                    complete_message += "\n이미 공대가 생성된 상태라 상비군으로도 등록되었습니다."

                if sent_to_channel:
                    await interaction.edit_original_response(
                        content=complete_message,
                        embed=None,
                        view=None,
                    )
                else:
                    extra_reason = send_fail_reason or "채널에 공개 메시지를 전송하지 못했습니다."
                    await interaction.edit_original_response(
                        content=f"{complete_message}\n공개 메시지 전송 실패: {extra_reason}",
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
                    content=result.get("message"),
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
                    content=result.get("message"),
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

            else:
                await interaction.edit_original_response(
                    content=result["message"],
                    embed=None,
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
                content=f"오류가 발생했습니다: {exc}",
                embed=None,
                view=None,
            )
