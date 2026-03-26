from __future__ import annotations

import discord
from discord.ui import View, Button, Select

from utils.constants import JOB_OPTIONS


def jobs_to_text(jobs: list[str]) -> str:
    return ", ".join(jobs) if jobs else "없음"


def build_rule_home_embed(rule, status_message: str | None = None) -> discord.Embed:
    embed = discord.Embed(
        title="공대 생성 규칙",
        description="현재 규칙 상태를 확인하고 수정할 수 있습니다.",
    )

    embed.add_field(
        name="1파티",
        value=(
            f"우선 직업: {jobs_to_text(rule.party1_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(rule.party1_preferred_jobs)}"
        ),
        inline=False,
    )

    embed.add_field(
        name="2파티",
        value=(
            f"우선 직업: {jobs_to_text(rule.party2_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(rule.party2_preferred_jobs)}"
        ),
        inline=False,
    )

    if status_message:
        embed.add_field(name="안내", value=status_message, inline=False)

    return embed


def build_build_home_embed(active_result, rule, status_message: str | None = None) -> discord.Embed:
    if active_result is None:
        embed = discord.Embed(
            title=f"{rule.raid_name} 공대 관리",
            description="현재 생성된 공대 결과가 없습니다.",
        )
    else:
        embed = discord.Embed(
            title=f"{active_result.raid_name} 공대 관리",
            description=(
                "현재 공대 생성 결과 요약\n\n"
                f"총 신청자: {active_result.total_applicants}명\n"
                f"정식 공대 {active_result.full_group_count}개 / "
                f"임시 공대 {active_result.temp_group_count}개 / "
                f"대기 인원 {active_result.waiting_count}명"
            ),
        )

    if status_message:
        embed.add_field(name="안내", value=status_message, inline=False)

    return embed


# 1차 화면 View
class PartyRuleHomeView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
    ):
        super().__init__(timeout=300)
        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service

    @discord.ui.button(label="규칙 수정", style=discord.ButtonStyle.primary, row=0)
    async def edit_rule_button(self, interaction: discord.Interaction, button: Button):
        edit_view = PartyRuleEditView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
        embed = build_rule_edit_embed(
            party1_priority_jobs=self.rule.party1_priority_jobs,
            party1_preferred_jobs=self.rule.party1_preferred_jobs,
            party2_priority_jobs=self.rule.party2_priority_jobs,
            party2_preferred_jobs=self.rule.party2_preferred_jobs,
        )
        await interaction.response.edit_message(embed=embed, view=edit_view)

    @discord.ui.button(label="규칙 초기화", style=discord.ButtonStyle.danger, row=0)
    async def reset_rule_button(self, interaction: discord.Interaction, button: Button):
        reset_rule = self.party_rule_service.reset_rule(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
            raid_name=self.rule.raid_name,
        )
        self.rule = reset_rule

        embed = build_rule_home_embed(
            reset_rule,
            status_message="규칙을 초기화했습니다.",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="다음", style=discord.ButtonStyle.success, row=1)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        active_result = self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )

        build_view = PartyBuildHomeView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
        embed = build_build_home_embed(active_result, self.rule)
        await interaction.response.edit_message(embed=embed, view=build_view)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=1)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(view=None)


# 2차 화면 View
class PartyBuildHomeView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
    ):
        super().__init__(timeout=300)
        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service

    @discord.ui.button(label="결과 확인", style=discord.ButtonStyle.primary, row=0)
    async def view_result_button(self, interaction: discord.Interaction, button: Button):
        active_result = self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )
        if active_result is None:
            embed = build_build_home_embed(
                None,
                self.rule,
                status_message="생성된 공대 결과가 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return

        embed = build_party_result_embed(active_result)
        detail_view = PartyResultDetailView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
        await interaction.response.edit_message(embed=embed, view=detail_view)

    @discord.ui.button(label="공대 생성", style=discord.ButtonStyle.success, row=0)
    async def build_button(self, interaction: discord.Interaction, button: Button):
        loading_embed = discord.Embed(
            title="공대 생성 중",
            description="신청자 최신 정보를 조회하고 공대를 생성하고 있습니다.",
        )
        await interaction.response.edit_message(embed=loading_embed, view=None)

        try:
            await self.party_builder_service.build_parties(
                guild_id=self.rule.guild_id,
                channel_id=self.rule.channel_id,
                created_by=interaction.user.id,
            )
            active_result = self.party_manage_service.get_active_build_result(
                guild_id=self.rule.guild_id,
                channel_id=self.rule.channel_id,
            )
            embed = build_build_home_embed(
                active_result,
                self.rule,
                status_message="공대 생성을 완료했습니다.",
            )
        except Exception as e:
            embed = build_build_home_embed(
                self.party_manage_service.get_active_build_result(
                    guild_id=self.rule.guild_id,
                    channel_id=self.rule.channel_id,
                ),
                self.rule,
                status_message=f"공대 생성 실패: {e}",
            )

        view = PartyBuildHomeView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
        await interaction.edit_original_response(embed=embed, view=view)

    @discord.ui.button(label="공대 초기화", style=discord.ButtonStyle.danger, row=0)
    async def reset_build_button(self, interaction: discord.Interaction, button: Button):
        reset_ok = self.party_manage_service.reset_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )

        status_message = "공대 결과를 초기화했습니다." if reset_ok else "초기화할 공대 결과가 없습니다."
        embed = build_build_home_embed(None, self.rule, status_message=status_message)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="공대 수정", style=discord.ButtonStyle.primary, row=1)
    async def modify_button(self, interaction: discord.Interaction, button: Button):
        active_result = self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )
        if active_result is None:
            embed = build_build_home_embed(
                None,
                self.rule,
                status_message="수정할 공대 결과가 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return

        modify_view = PartyModifyView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
        embed = build_party_modify_embed(active_result)
        await interaction.response.edit_message(embed=embed, view=modify_view)

    @discord.ui.button(label="결과 공유", style=discord.ButtonStyle.secondary, row=1)
    async def share_button(self, interaction: discord.Interaction, button: Button):
        active_result = self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )
        if active_result is None:
            embed = build_build_home_embed(
                None,
                self.rule,
                status_message="공유할 공대 결과가 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return

        await interaction.channel.send(embed=build_party_result_embed(active_result))
        embed = build_build_home_embed(
            active_result,
            self.rule,
            status_message="공대 결과를 채널에 공유했습니다.",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="뒤로가기", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        rule_view = PartyRuleHomeView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
        embed = build_rule_home_embed(self.rule)
        await interaction.response.edit_message(embed=embed, view=rule_view)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=1)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(view=None)


# 결과 상세 화면에도 뒤로가기 추가
class PartyResultDetailView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
    ):
        super().__init__(timeout=300)
        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service

    @discord.ui.button(label="뒤로가기", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        active_result = self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )
        embed = build_build_home_embed(active_result, self.rule)
        view = PartyBuildHomeView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
        await interaction.response.edit_message(embed=embed, view=view)
