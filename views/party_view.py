from __future__ import annotations

import discord
from discord.ui import View, Select, Button

from utils.constants import JOB_OPTIONS


def jobs_to_text(jobs: list[str]) -> str:
    return ", ".join(jobs) if jobs else "없음"


def build_rule_detail_embed(rule) -> discord.Embed:
    embed = discord.Embed(
        title="공대 생성 규칙",
        description=(
            "각 파티에 우선 배치할 직업과 선호 직업을 확인할 수 있습니다."
        ),
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

    return embed


def build_rule_edit_embed(
    party1_priority_jobs: list[str],
    party1_preferred_jobs: list[str],
    party2_priority_jobs: list[str],
    party2_preferred_jobs: list[str],
) -> discord.Embed:
    embed = discord.Embed(
        title="공대 생성 규칙 수정",
        description=(
            "각 파티에 우선 배치할 직업과 선호 직업을 설정해주세요.\n"
            "선호 직업은 필요한 경우에만 선택하면 됩니다.\n\n"
            "※ '없음'을 선택하면 다른 선택은 해제됩니다.\n"
            "※ 직업은 복수 선택할 수 있습니다."
        ),
    )

    embed.add_field(
        name="1파티",
        value=(
            f"우선 직업: {jobs_to_text(party1_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(party1_preferred_jobs)}"
        ),
        inline=False,
    )

    embed.add_field(
        name="2파티",
        value=(
            f"우선 직업: {jobs_to_text(party2_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(party2_preferred_jobs)}"
        ),
        inline=False,
    )

    return embed


class JobMultiSelect(Select):
    def __init__(
        self,
        placeholder: str,
        current_values: list[str],
        on_change_callback,
    ):
        options = []
        for job in JOB_OPTIONS:
            is_default = job in current_values

            options.append(
                discord.SelectOption(
                    label=job,
                    value=job,
                    default=is_default,
                )
            )

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=len(JOB_OPTIONS),
            options=options,
        )

        self.on_change_callback = on_change_callback

    async def callback(self, interaction: discord.Interaction):
        selected_values = list(self.values)
    
        normalized_values = []
    
        # "없음"만 단독 선택한 경우
        if selected_values == ["없음"]:
            normalized_values = []
        else:
            # 다른 항목이 있으면 "없음"은 제거
            for value in selected_values:
                if value == "없음":
                    continue
                if value not in normalized_values:
                    normalized_values.append(value)
    
        await self.on_change_callback(interaction, normalized_values)


class SaveRuleButton(Button):
    def __init__(self):
        super().__init__(label="저장", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        updated_rule = view.party_rule_service.update_rule(
            guild_id=view.rule.guild_id,
            channel_id=view.rule.channel_id,
            raid_name=view.rule.raid_name,
            party1_priority_jobs=view.party1_priority_jobs,
            party1_preferred_jobs=view.party1_preferred_jobs,
            party2_priority_jobs=view.party2_priority_jobs,
            party2_preferred_jobs=view.party2_preferred_jobs,
        )

        detail_view = PartyRuleDetailView(
            rule=updated_rule,
            party_rule_service=view.party_rule_service,
        )
        detail_embed = build_rule_detail_embed(updated_rule)

        await interaction.response.edit_message(
            embed=detail_embed,
            view=detail_view,
        )


class CancelEditButton(Button):
    def __init__(self):
        super().__init__(label="취소", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        latest_rule = view.party_rule_service.get_or_create_rule(
            guild_id=view.rule.guild_id,
            channel_id=view.rule.channel_id,
            raid_name=view.rule.raid_name,
        )

        detail_view = PartyRuleDetailView(
            rule=latest_rule,
            party_rule_service=view.party_rule_service,
        )
        detail_embed = build_rule_detail_embed(latest_rule)

        await interaction.response.edit_message(
            embed=detail_embed,
            view=detail_view,
        )


class PartyRuleEditView(View):
    def __init__(self, rule, party_rule_service):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service

        self.party1_priority_jobs = list(rule.party1_priority_jobs)
        self.party1_preferred_jobs = list(rule.party1_preferred_jobs)
        self.party2_priority_jobs = list(rule.party2_priority_jobs)
        self.party2_preferred_jobs = list(rule.party2_preferred_jobs)

        self._build_components()

    def _build_components(self):
        self.clear_items()

        self.add_item(
            JobMultiSelect(
                placeholder="1파티 우선 직업 선택",
                current_values=self.party1_priority_jobs,
                on_change_callback=self._on_party1_priority_change,
            )
        )

        self.add_item(
            JobMultiSelect(
                placeholder="1파티 선호 직업 선택",
                current_values=self.party1_preferred_jobs,
                on_change_callback=self._on_party1_preferred_change,
            )
        )

        self.add_item(
            JobMultiSelect(
                placeholder="2파티 우선 직업 선택",
                current_values=self.party2_priority_jobs,
                on_change_callback=self._on_party2_priority_change,
            )
        )

        self.add_item(
            JobMultiSelect(
                placeholder="2파티 선호 직업 선택",
                current_values=self.party2_preferred_jobs,
                on_change_callback=self._on_party2_preferred_change,
            )
        )

        self.add_item(SaveRuleButton())
        self.add_item(CancelEditButton())

    async def _refresh(self, interaction: discord.Interaction):
        self._build_components()

        edit_embed = build_rule_edit_embed(
            party1_priority_jobs=self.party1_priority_jobs,
            party1_preferred_jobs=self.party1_preferred_jobs,
            party2_priority_jobs=self.party2_priority_jobs,
            party2_preferred_jobs=self.party2_preferred_jobs,
        )

        await interaction.response.edit_message(
            embed=edit_embed,
            view=self,
        )

    async def _on_party1_priority_change(
        self,
        interaction: discord.Interaction,
        selected_values: list[str],
    ):
        self.party1_priority_jobs = selected_values
        await self._refresh(interaction)

    async def _on_party1_preferred_change(
        self,
        interaction: discord.Interaction,
        selected_values: list[str],
    ):
        self.party1_preferred_jobs = selected_values
        await self._refresh(interaction)

    async def _on_party2_priority_change(
        self,
        interaction: discord.Interaction,
        selected_values: list[str],
    ):
        self.party2_priority_jobs = selected_values
        await self._refresh(interaction)

    async def _on_party2_preferred_change(
        self,
        interaction: discord.Interaction,
        selected_values: list[str],
    ):
        self.party2_preferred_jobs = selected_values
        await self._refresh(interaction)


class PartyRuleDetailView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        
    @discord.ui.button(label="수정", style=discord.ButtonStyle.primary)
    async def edit_button(self, interaction: discord.Interaction, button: Button):
        edit_view = PartyRuleEditView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
        )

        edit_embed = build_rule_edit_embed(
            party1_priority_jobs=self.rule.party1_priority_jobs,
            party1_preferred_jobs=self.rule.party1_preferred_jobs,
            party2_priority_jobs=self.rule.party2_priority_jobs,
            party2_preferred_jobs=self.rule.party2_preferred_jobs,
        )

        await interaction.response.edit_message(
            embed=edit_embed,
            view=edit_view,
        )

    @discord.ui.button(label="초기화", style=discord.ButtonStyle.danger)
    async def reset_button(self, interaction: discord.Interaction, button: Button):
        reset_rule = self.party_rule_service.reset_rule(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
            raid_name=self.rule.raid_name,
        )

        self.rule = reset_rule
        detail_embed = build_rule_detail_embed(reset_rule)

        await interaction.response.edit_message(
            embed=detail_embed,
            view=self,
        )

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(view=None)

def build_party_build_result_embed(result) -> discord.Embed:
    embed = discord.Embed(
        title="공대 생성 결과",
        description=(
            f"레이드: {result.raid_name}\n"
            f"총 신청자: {result.total_applicants}명\n"
            f"정식 공대: {result.full_group_count}개\n"
            f"임시 공대: {result.temp_group_count}개\n"
            f"대기 인원: {result.waiting_count}명"
        ),
    )

    for party in result.parties:
        group_label = f"{party.group_no}공대"
        if party.is_temp_group:
            group_label += " (임시)"

        member_lines = []
        for member in party.members:
            member_lines.append(
                f"{member.slot_no}. {member.character_name} / {member.job} / {member.combat_power:,}"
            )

        if not member_lines:
            member_lines.append("배치 인원 없음")

        embed.add_field(
            name=f"{group_label} {party.party_no}파티 (총 전투력: {party.total_combat_power:,})",
            value="\n".join(member_lines),
            inline=False,
        )

    if result.waiting_members:
        waiting_lines = []
        for idx, member in enumerate(result.waiting_members, start=1):
            waiting_lines.append(
                f"{idx}. {member.character_name} / {member.job} / {member.combat_power:,}"
            )

        embed.add_field(
            name="대기 인원",
            value="\n".join(waiting_lines),
            inline=False,
        )

    if hasattr(result, "refresh_summary") and result.refresh_summary is not None:
        refresh_lines = [
            f"최신 정보 갱신 성공: {result.refresh_summary.updated_count}명",
            f"최신 정보 갱신 실패: {result.refresh_summary.failed_count}명",
        ]
        if result.refresh_summary.failed_characters:
            failed_names = ", ".join(result.refresh_summary.failed_characters[:10])
            refresh_lines.append(f"실패 캐릭터: {failed_names}")

        embed.add_field(
            name="신청자 정보 갱신 결과",
            value="\n".join(refresh_lines),
            inline=False,
        )

    return embed
