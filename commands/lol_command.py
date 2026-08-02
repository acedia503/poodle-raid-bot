import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils.permissions import is_admin
from views.lol_main_view import (
    LolApplicationModal,
    LolCancelConfirmView,
    LolMainView,
    LolResetConfirmView,
)

LOL_LIST_BODY_MAX_LENGTH = 3900


class LolCommand(commands.Cog):
    def __init__(self, bot, service):
        self.bot = bot
        self.service = service

    # ---------- embed helpers ----------

    def _notice_embed(self, title: str, description: str = "", color=None) -> discord.Embed:
        embed = discord.Embed(title=title, color=color or discord.Color.blurple())
        if description:
            embed.description = description
        return embed

    def _error_embed(self, title: str, description: str = "") -> discord.Embed:
        embed = discord.Embed(title=title, color=discord.Color.red())
        if description:
            embed.description = description
        return embed

    def _location_error_embed(self) -> discord.Embed:
        return self._error_embed(
            "사용할 수 없는 위치입니다.",
            "서버 채널에서만 사용할 수 있습니다.",
        )

    def _build_main_embed(self, application) -> discord.Embed:
        description = application.riot_id if application else "신청 내역이 없습니다."
        return discord.Embed(
            title="🎮 롤 현재 신청 내역",
            description=description,
            color=discord.Color.blurple(),
        )

    def _resolve_display_name(self, guild: discord.Guild | None, app) -> str:
        if guild is not None:
            member = guild.get_member(app.user_id)
            if member is not None:
                return member.display_name

        return app.user_name

    def _build_list_embed(
        self,
        applications,
        guild: discord.Guild | None = None,
    ) -> discord.Embed:
        if not applications:
            return discord.Embed(
                title="🎮 롤 신청 목록",
                description="신청 내역이 없습니다.\n\n총 0명",
                color=discord.Color.blurple(),
            )

        lines = [
            f"{idx}. {self._resolve_display_name(guild, app)} - {app.riot_id}"
            for idx, app in enumerate(applications, start=1)
        ]

        body = "\n".join(lines)

        # Discord Embed description 길이 제한을 명백히 초과하는 경우를 대비한 최소한의 방어
        if len(body) > LOL_LIST_BODY_MAX_LENGTH:
            truncated_body = ""
            for line in lines:
                candidate = f"{truncated_body}\n{line}" if truncated_body else line
                if len(candidate) > LOL_LIST_BODY_MAX_LENGTH:
                    break
                truncated_body = candidate
            body = f"{truncated_body}\n... (목록이 길어 일부만 표시됩니다)"

        description = f"{body}\n\n총 {len(applications)}명"

        return discord.Embed(
            title="🎮 롤 신청 목록",
            description=description,
            color=discord.Color.blurple(),
        )

    def _build_main_view(self, interaction: discord.Interaction) -> LolMainView:
        return LolMainView(
            apply_callback=self._apply_callback,
            cancel_callback=self._cancel_callback,
            list_callback=self._list_callback,
            reset_callback=self._reset_callback if is_admin(interaction) else None,
        )

    # ---------- main screen ----------

    async def _render_main(
        self,
        interaction: discord.Interaction,
        *,
        first_response: bool,
    ):
        if interaction.guild is None or interaction.channel is None:
            embed = self._location_error_embed()
            if first_response:
                await interaction.response.send_message(
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

        application = await asyncio.to_thread(
            self.service.get_my_application,
            interaction.guild.id,
            interaction.user.id,
        )

        embed = self._build_main_embed(application)
        view = self._build_main_view(interaction)

        if first_response:
            await interaction.response.send_message(
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

    @app_commands.command(name="롤", description="롤 신청 관리 메뉴")
    async def lol(self, interaction: discord.Interaction):
        try:
            await self._render_main(interaction, first_response=True)
        except Exception as exc:
            print("[LOL][MAIN_ERROR]", repr(exc))
            embed = self._error_embed(
                "오류가 발생했습니다.",
                "처리 중 예상하지 못한 오류가 발생했습니다.",
            )
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed, view=None)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _back_callback(self, interaction: discord.Interaction):
        await self._render_main(interaction, first_response=False)

    # ---------- apply ----------

    async def _apply_callback(self, interaction: discord.Interaction):
        async def on_submit(modal_interaction: discord.Interaction, riot_id: str):
            await self._process_apply(modal_interaction, riot_id)

        await interaction.response.send_modal(LolApplicationModal(on_submit))

    async def _process_apply(self, interaction: discord.Interaction, riot_id: str):
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.edit_original_response(
                embed=self._location_error_embed(),
                view=None,
            )
            return

        try:
            result = await asyncio.to_thread(
                self.service.apply,
                interaction.guild.id,
                interaction.user.id,
                interaction.user.display_name,
                riot_id,
            )
        except Exception as exc:
            print(
                "[LOL][APPLY_ERROR]",
                f"guild_id={interaction.guild.id}",
                f"user_id={interaction.user.id}",
                repr(exc),
            )
            await interaction.edit_original_response(
                embed=self._error_embed(
                    "오류가 발생했습니다.",
                    "처리 중 예상하지 못한 오류가 발생했습니다.",
                ),
                view=None,
            )
            return

        action = result["action"]

        if action == "invalid_format":
            embed = self._error_embed(
                "❌ 롤 아이디는 #태그까지 입력해주세요.",
                "예시: Acedia#KR1",
            )
            await interaction.edit_original_response(embed=embed, view=None)
            return

        if action == "duplicate":
            embed = self._error_embed("❌ 이미 신청된 롤 아이디입니다.")
            await interaction.edit_original_response(embed=embed, view=None)
            return

        application = result["application"]

        if action == "created":
            embed = discord.Embed(
                title="✅ 롤 신청 완료",
                description=application.riot_id,
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="✅ 롤 신청 변경 완료",
                description=application.riot_id,
                color=discord.Color.green(),
            )

        await interaction.edit_original_response(embed=embed, view=None)

    # ---------- cancel ----------

    async def _cancel_callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.edit_message(
                content=None,
                embed=self._location_error_embed(),
                view=None,
            )
            return

        application = await asyncio.to_thread(
            self.service.get_my_application,
            interaction.guild.id,
            interaction.user.id,
        )

        if application is None:
            await interaction.response.edit_message(
                content=None,
                embed=self._notice_embed(
                    "취소할 롤 신청 내역이 없습니다.",
                    color=discord.Color.orange(),
                ),
                view=None,
            )
            return

        embed = discord.Embed(
            title="🎮 롤 신청 취소",
            description=f"{application.riot_id}\n\n정말 취소하시겠습니까?",
            color=discord.Color.orange(),
        )
        view = LolCancelConfirmView(
            confirm_callback=self._cancel_confirm_callback,
            back_callback=self._back_callback,
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=view,
        )

    async def _cancel_confirm_callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.edit_message(
                content=None,
                embed=self._location_error_embed(),
                view=None,
            )
            return

        deleted = await asyncio.to_thread(
            self.service.cancel,
            interaction.guild.id,
            interaction.user.id,
        )

        if deleted:
            embed = self._notice_embed(
                "✅ 롤 신청이 취소되었습니다.",
                color=discord.Color.green(),
            )
        else:
            embed = self._notice_embed(
                "취소할 롤 신청 내역이 없습니다.",
                color=discord.Color.orange(),
            )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None,
        )

    # ---------- list ----------

    async def _list_callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.edit_message(
                content=None,
                embed=self._location_error_embed(),
                view=None,
            )
            return

        applications = await asyncio.to_thread(
            self.service.get_all,
            interaction.guild.id,
        )

        embed = self._build_list_embed(applications, guild=interaction.guild)

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None,
        )

    # ---------- admin reset ----------

    async def _reset_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            await interaction.response.edit_message(
                content=None,
                embed=self._error_embed("❌ 관리자만 롤 신청 목록을 초기화할 수 있습니다."),
                view=None,
            )
            return

        if interaction.guild is None:
            await interaction.response.edit_message(
                content=None,
                embed=self._location_error_embed(),
                view=None,
            )
            return

        count = await asyncio.to_thread(
            self.service.count,
            interaction.guild.id,
        )

        embed = discord.Embed(
            title="⚠️ 롤 신청 목록 초기화",
            description=(
                f"현재 {count}명의 신청 내역이 있습니다.\n"
                "초기화한 내역은 복구할 수 없습니다."
            ),
            color=discord.Color.orange(),
        )
        view = LolResetConfirmView(
            confirm_callback=self._reset_confirm_callback,
            back_callback=self._back_callback,
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=view,
        )

    async def _reset_confirm_callback(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            await interaction.response.edit_message(
                content=None,
                embed=self._error_embed("❌ 관리자만 롤 신청 목록을 초기화할 수 있습니다."),
                view=None,
            )
            return

        if interaction.guild is None:
            await interaction.response.edit_message(
                content=None,
                embed=self._location_error_embed(),
                view=None,
            )
            return

        deleted_count = await asyncio.to_thread(
            self.service.reset,
            interaction.guild.id,
        )

        embed = discord.Embed(
            title="✅ 롤 신청 목록이 초기화되었습니다.",
            description=f"삭제된 신청 내역: {deleted_count}명",
            color=discord.Color.green(),
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None,
        )
