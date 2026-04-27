import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from views.application_view import RaceView, ServerView
from views.application_result_view import ApplicationResultView
from views.application_main_view import ApplicationMainView, ApplicationCharacterModal
from views.application_cancel_view import ApplicationCancelSelectView

class ApplicationCommand(commands.Cog):
    
    @app_commands.command(name="신청", description="레이드 신청 메뉴")
    async def apply(self, interaction: discord.Interaction):
        try:
            if interaction.guild is None or interaction.channel is None:
                await interaction.response.send_message(
                    "서버 채널에서만 사용할 수 있습니다.",
                    ephemeral=True,
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
    
            async def my_applications_callback(inter: discord.Interaction):
                applications = await asyncio.to_thread(
                    self.service.repository.get_by_guild_and_user_id,
                    inter.guild.id,
                    inter.user.id,
                )
    
                if not applications:
                    await inter.response.edit_message(
                        content="신청 내역이 없습니다.",
                        embed=None,
                        view=None,
                    )
                    return
    
                lines = []
                for idx, app in enumerate(applications, start=1):
                    lines.append(
                        f"{idx}. **{app.raid_name}** | "
                        f"{app.character_name} | {app.job} | "
                        f"{app.item_level} | {app.combat_power:,}"
                    )
    
                embed = discord.Embed(
                    title="내 신청 내역",
                    description="\n".join(lines),
                )
    
                await inter.response.edit_message(
                    content=None,
                    embed=embed,
                    view=None,
                )

            async def cancel_callback(inter: discord.Interaction):
                applications = await asyncio.to_thread(
                    self.service.repository.get_by_guild_and_user_id,
                    inter.guild.id,
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
                        embed = self.message_service.build_application_result_embed(
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
                            embed=embed,
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
            
                    embed = discord.Embed(
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
                            embed=embed,
                            view=view,
                        )
                    else:
                        await refresh_inter.response.edit_message(
                            content=None,
                            embed=embed,
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
    
                embed = self.message_service.build_admin_application_list_embed(
                    result["raid_name"],
                    result["applications"],
                    show_identity=show_identity,
                )
    
                await inter.response.edit_message(
                    content="신청 현황",
                    embed=embed,
                    view=None,
                )
    
            await interaction.response.send_message(
                content="신청 메뉴를 선택하세요.",
                view=ApplicationMainView(
                    apply_callback=apply_callback,
                    my_applications_callback=my_applications_callback,
                    cancel_callback=cancel_callback,
                    status_callback=status_callback,
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
