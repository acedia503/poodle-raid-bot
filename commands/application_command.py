import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils.permissions import is_admin

from views.application_view import RaceView, ServerView
from views.application_result_view import ApplicationResultView
from views.application_main_view import ApplicationMainView, ApplicationCharacterModal
from views.application_cancel_view import ApplicationCancelButtonSelectView


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

    def _notice_embed(
        self,
        title: str,
        description: str,
        color: discord.Color | None = None,
    ) -> discord.Embed:
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
            return (
                "캐릭터 정보를 찾을 수 없습니다.\n\n"
                "입력한 캐릭터명, 종족, 서버가 맞는지 확인해주세요."
            )

        if "외부 API" in text or "API" in text:
            return (
                "캐릭터 정보 조회 중 문제가 발생했습니다.\n\n"
                "잠시 후 다시 시도해주세요.\n"
                "계속 실패하면 관리자에게 문의해주세요."
            )

        if "알 수 없는 종족" in text or "알 수 없는 서버" in text:
            return (
                "종족 또는 서버 정보가 올바르지 않습니다.\n\n"
                "다시 선택 후 신청해주세요."
            )

        return (
            "처리 중 예상하지 못한 오류가 발생했습니다.\n\n"
            f"오류 내용: {text}"
        )

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

    @app_commands.command(name="신청", description="레이드 신청 메뉴")
    async def apply(self, interaction: discord.Interaction):
        try:
            if interaction.guild is None or interaction.channel is None:
                await interaction.response.send_message(
                    content=None,
                    embed=self._error_embed(
                        "사용할 수 없는 위치입니다.",
                        "서버 채널에서만 사용할 수 있습니다.",
                    ),
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
            else:
                applications = await asyncio.to_thread(
                    self.service.repository.get_by_guild_and_user_id,
                    interaction.guild.id,
                    interaction.user.id,
                )
                title = "내 전체 신청 현황"

            if applications:
                lines = []
                for idx, app in enumerate(applications, start=1):
                    if channel_raid is not None:
                        lines.append(
                            f"{idx}. {app.character_name} | {app.job} | "
                            f"{app.item_level} | {app.combat_power:,}"
                        )
                    else:
                        lines.append(
                            f"{idx}. **{app.raid_name}** | "
                            f"{app.character_name} | {app.job} | "
                            f"{app.item_level} | {app.combat_power:,}"
                        )

                embed = discord.Embed(
                    title=title,
                    description="\n".join(lines),
                    color=discord.Color.blurple(),
                )
            else:
                embed = discord.Embed(
                    title=title,
                    description="신청 내역이 없습니다.",
                    color=discord.Color.blurple(),
                )

            if channel_raid is None:
                embed.add_field(
                    name="안내",
                    value="현재 채널에 매칭된 레이드가 없어 전체 신청 현황만 표시합니다.",
                    inline=False,
                )
                await interaction.response.send_message(
                    content=None,
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
                applications = await asyncio.to_thread(
                    self.service.repository.get_by_guild_raid_and_user_id,
                    inter.guild.id,
                    channel_raid.raid_name,
                    inter.user.id,
                )

                if not applications:
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
                            content=None,
                            embed=self._notice_embed(
                                "신청 취소 실패",
                                "이미 취소되었거나 존재하지 않는 신청입니다.",
                                discord.Color.orange(),
                            ),
                            view=None,
                        )
                    return

                selected_ids = set()

                async def select_cancel_callback(inter: discord.Interaction):
                    applications = await asyncio.to_thread(
                        self.service.repository.get_by_guild_raid_and_user_id,
                        inter.guild.id,
                        channel_raid.raid_name,
                        inter.user.id,
                    )
                
                    if not applications:
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
                        lines = []
                        for idx, app in enumerate(apps, start=1):
                            mark = "✅" if app.id in ids else "⬜"
                            lines.append(
                                f"{mark} {idx}. {app.character_name} | {app.job} | "
                                f"{app.item_level} | {app.combat_power:,}"
                            )
                
                        embed = discord.Embed(
                            title="신청 취소 대상 선택",
                            description="\n".join(lines),
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
                                embed=embed,
                                view=view,
                                content=None,
                            )
                        else:
                            await refresh_inter.response.edit_message(
                                embed=embed,
                                view=view,
                                content=None,
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
                        await self.apply(back_inter)
                
                    await refresh_view(inter, applications, selected_ids)

            async def cancel_all_callback(inter: discord.Interaction):
                applications = await asyncio.to_thread(
                    self.service.repository.get_by_guild_raid_and_user_id,
                    inter.guild.id,
                    channel_raid.raid_name,
                    inter.user.id,
                )
            
                if not applications:
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
                for app in applications:
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
                
                async def refresh_cancel_view(refresh_inter, apps, ids):
                    lines = []
                    for idx, app in enumerate(apps, start=1):
                        checked = "✅" if app.id in ids else "⬜"
                        lines.append(
                            f"{checked} {idx}. {app.character_name} | {app.job} | "
                            f"{app.item_level} | {app.combat_power:,}"
                        )

                    cancel_list_embed = discord.Embed(
                        title="신청 취소 대상 선택",
                        description="\n".join(lines),
                        color=discord.Color.orange(),
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
                            content=None,
                            embed=self._notice_embed(
                                "선택된 신청이 없습니다.",
                                "취소할 신청을 먼저 선택해주세요.",
                                discord.Color.orange(),
                            ),
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
                        content=None,
                        embed=self._notice_embed(
                            "신청 취소 완료",
                            f"신청 {cancelled_count}건을 취소했습니다.",
                            discord.Color.green(),
                        ),
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
                        content=None,
                        embed=self._notice_embed(
                            "신청 취소 완료",
                            f"신청 {cancelled_count}건을 취소했습니다.",
                            discord.Color.green(),
                        ),
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
                        content=None,
                        embed=self._notice_embed(
                            "레이드 신청 현황을 볼 수 없습니다.",
                            "현재 채널에 매칭된 레이드가 없습니다.",
                            discord.Color.orange(),
                        ),
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
                    content=None,
                    embed=status_embed,
                    view=None,
                )

            admin_delete_callback = None
            if is_admin(interaction):
                async def admin_delete_callback(inter: discord.Interaction):
                    await inter.response.edit_message(
                        content=None,
                        embed=self._notice_embed(
                            "관리자용 신청 삭제",
                            "관리자 삭제 기능은 다음 단계에서 연결됩니다.",
                            discord.Color.orange(),
                        ),
                        view=None,
                    )

            await interaction.response.send_message(
                content=None,
                embed=embed,
                view=ApplicationMainView(
                    application_count=len(applications),
                    apply_callback=apply_callback,
                    cancel_callback=cancel_callback,
                    select_cancel_callback=select_cancel_callback,
                    cancel_all_callback=cancel_all_callback,
                    status_callback=status_callback,
                    admin_delete_callback=admin_delete_callback,
                ),
                ephemeral=True,
            )

        except Exception as exc:
            await self._respond_error(interaction, exc)

    async def _process(self, interaction, character_name, race, server, show_identity: bool):
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
