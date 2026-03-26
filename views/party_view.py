from __future__ import annotations

import discord
from discord.ui import View, Select, Button
from collections import defaultdict

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
            party_builder_service=view.party_builder_service,
            party_manage_service=view.party_manage_service,
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
            party_builder_service=view.party_builder_service,
            party_manage_service=view.party_manage_service,
        )
        detail_embed = build_rule_detail_embed(latest_rule)

        await interaction.response.edit_message(
            embed=detail_embed,
            view=detail_view,
        )


class PartyRuleEditView(View):
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
        party_modify_service,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        
    @discord.ui.button(label="규칙 수정", style=discord.ButtonStyle.primary, row=0)
    async def edit_button(self, interaction: discord.Interaction, button: Button):
        edit_view = PartyRuleEditView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
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

    @discord.ui.button(label="규칙 초기화", style=discord.ButtonStyle.danger, row=0)
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

    @discord.ui.button(label="공대 생성", style=discord.ButtonStyle.success, row=1)
    async def build_button(self, interaction: discord.Interaction, button: Button):
        loading_embed = discord.Embed(
            title="공대 생성 중",
            description="신청자 최신 정보를 조회하고 공대를 생성하고 있습니다.\n잠시만 기다려주세요.",
        )
    
        await interaction.response.edit_message(
            embed=loading_embed,
            view=None,
        )
    
        try:
            result = await self.party_builder_service.build_parties(
                guild_id=self.rule.guild_id,
                channel_id=self.rule.channel_id,
                created_by=interaction.user.id,
            )
            result_embed = build_party_result_embed(result)
            await interaction.edit_original_response(
                embed=result_embed,
                view=self,
            )
        except Exception as e:
            error_embed = discord.Embed(
                title="공대 생성 실패",
                description=str(e),
            )
            await interaction.edit_original_response(
                embed=error_embed,
                view=self,
            )


    @discord.ui.button(label="결과 확인", style=discord.ButtonStyle.secondary, row=1)
    async def view_result_button(self, interaction: discord.Interaction, button: Button):
        result = self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )

        if result is None:
            await interaction.response.send_message(
                "생성된 공대 결과가 없습니다.",
                ephemeral=True,
            )
            return

        result_embed = build_party_result_embed(result)
        await interaction.response.edit_message(
            embed=result_embed,
            view=self,
        )

    @discord.ui.button(label="공대 초기화", style=discord.ButtonStyle.danger, row=1)
    async def reset_build_button(self, interaction: discord.Interaction, button: Button):
        reset_ok = self.party_manage_service.reset_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )

        if not reset_ok:
            await interaction.response.send_message(
                "초기화할 공대 생성 결과가 없습니다.",
                ephemeral=True,
            )
            return

        detail_embed = build_rule_detail_embed(self.rule)
        await interaction.response.edit_message(
            embed=detail_embed,
            view=self,
        )

    @discord.ui.button(label="공대 수정", style=discord.ButtonStyle.primary, row=2)
    async def modify_button(self, interaction: discord.Interaction, button: Button):
        active_result = self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )
        if active_result is None:
            await interaction.response.send_message(
                "수정할 공대 생성 결과가 없습니다.",
                ephemeral=True,
            )
            return

        modify_view = PartyModifyView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
        )
        modify_embed = build_party_modify_embed(active_result)

        await interaction.response.edit_message(
            embed=modify_embed,
            view=modify_view,
        )
        
    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=2)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(view=None)


def build_party_result_embed(result) -> discord.Embed:
    embed = discord.Embed(
        title=f"{result.raid_name} 공대 생성 결과",
        color=discord.Color.green(),
    )

    # 상단 요약
    embed.description = (
        f"총 신청자: {result.total_applicants}명\n"
        f"정식 공대 {result.full_group_count}개 / "
        f"임시 공대 {result.temp_group_count}개 / "
        f"대기 인원 {result.waiting_count}명"
    )

    # 그룹별 정리
    group_map = defaultdict(list)
    for party in result.parties:
        group_map[party.group_no].append(party)

    # 공대별 출력
    for group_no in sorted(group_map.keys()):
        parties = sorted(group_map[group_no], key=lambda p: p.party_no)

        value_lines = []

        for party in parties:
            value_lines.append(f"**{party.party_no}파티 | 총 전투력: {party.total_combat_power:,}**")

            for idx, member in enumerate(party.members, start=1):
                value_lines.append(
                    f"{idx}. {member.character_name} ({member.job}) "
                    f"[{member.combat_power:,}]"
                )

            value_lines.append("")  # 줄바꿈

        embed.add_field(
            name=f"✨{group_no}공대",
            value="\n".join(value_lines),
            inline=False,
        )

    # 대기 인원
    if result.waiting_members:
        waiting_lines = []
        for idx, member in enumerate(result.waiting_members, start=1):
            waiting_lines.append(
                f"{idx}. {member.character_name} ({member.job}) "
                f"[{member.combat_power:,}]"
            )

        embed.add_field(
            name="🕓 대기 인원",
            value="\n".join(waiting_lines),
            inline=False,
        )

    return embed


def build_party_modify_embed(active_result) -> discord.Embed:
    embed = discord.Embed(
        title=f"{active_result.raid_name} 공대 수정",
        description=(
            f"총 신청자: {active_result.total_applicants}명\n"
            f"정식 공대 {active_result.full_group_count}개 / "
            f"임시 공대 {active_result.temp_group_count}개 / "
            f"대기 인원 {active_result.waiting_count}명\n\n"
            "수정할 작업을 선택하세요.\n"
            "- 대기 인원 편입\n"
            "- 공대원 제외\n"
            "- 대기 인원과 교체"
        ),
    )
    return embed


class WaitingMemberSelect(Select):
    def __init__(self, waiting_members: list):
        options = []

        if not waiting_members:
            options.append(
                discord.SelectOption(
                    label="대기 인원 없음",
                    value="none",
                    description="선택 가능한 대기 인원이 없습니다.",
                )
            )
            disabled = True
        else:
            for member in waiting_members[:25]:
                options.append(
                    discord.SelectOption(
                        label=f"{member.character_name} ({member.job})",
                        value=str(member.id if hasattr(member, "id") else member["id"]),
                        description=f"{member.combat_power:,}",
                    )
                )
            disabled = False

        super().__init__(
            placeholder="대기 인원 선택",
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.defer()
            return

        view: PartyModifyView = self.view
        view.selected_waiting_id = int(self.values[0])
        await view.refresh(interaction)


class PartySlotSelect(Select):
    def __init__(self, parties: list):
        options = []

        for party in parties:
            for member in party.members:
                slot_no = getattr(member, "slot_no", None)
                if slot_no is None:
                    slot_no = party.members.index(member) + 1

                member_id = getattr(member, "slot_id", None)
                if member_id is None:
                    member_id = getattr(member, "id", None)

                if member_id is None:
                    continue

                options.append(
                    discord.SelectOption(
                        label=f"{party.group_no}공대 {party.party_no}파티 {slot_no}번 - {member.character_name}",
                        value=str(member_id),
                        description=f"{member.job} / {member.combat_power:,}",
                    )
                )

        if not options:
            options.append(
                discord.SelectOption(
                    label="공대원 없음",
                    value="none",
                    description="선택 가능한 공대원이 없습니다.",
                )
            )
            disabled = True
        else:
            disabled = False

        super().__init__(
            placeholder="공대원 선택",
            min_values=1,
            max_values=1,
            options=options[:25],
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.defer()
            return

        view: PartyModifyView = self.view
        view.selected_slot_id = int(self.values[0])
        await view.refresh(interaction)


class TargetPartySelect(Select):
    def __init__(self, parties: list):
        seen = set()
        options = []

        for party in parties:
            key = (party.group_no, party.party_no)
            if key in seen:
                continue
            seen.add(key)

            label = f"{party.group_no}공대 {party.party_no}파티"
            if party.is_temp_group:
                label += " (임시)"

            options.append(
                discord.SelectOption(
                    label=label,
                    value=f"{party.group_no}:{party.party_no}",
                    description=f"현재 인원 {len(party.members)}명",
                )
            )

        super().__init__(
            placeholder="편입할 대상 파티 선택",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        view: PartyModifyView = self.view
        group_no, party_no = self.values[0].split(":")
        view.selected_group_no = int(group_no)
        view.selected_party_no = int(party_no)
        await view.refresh(interaction)


class PartyModifyView(View):
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

        self.selected_waiting_id: int | None = None
        self.selected_slot_id: int | None = None
        self.selected_group_no: int | None = None
        self.selected_party_no: int | None = None

        self._build_components()

    def _get_active_result(self):
        return self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )

    def _build_components(self):
        self.clear_items()

        active_result = self._get_active_result()
        if active_result is None:
            return

        self.add_item(WaitingMemberSelect(active_result.waiting_members))
        self.add_item(PartySlotSelect(active_result.parties))
        self.add_item(TargetPartySelect(active_result.parties))

        self.add_item(WaitingToPartyButton())
        self.add_item(RemoveToWaitingButton())
        self.add_item(SwapWithWaitingButton())
        self.add_item(BackToResultButton())

    async def refresh(self, interaction: discord.Interaction):
        self._build_components()
        active_result = self._get_active_result()

        if active_result is None:
            embed = discord.Embed(
                title="공대 수정",
                description="현재 생성된 공대 결과가 없습니다.",
            )
        else:
            embed = build_party_modify_embed(active_result)

            status_lines = []
            if self.selected_waiting_id is not None:
                status_lines.append(f"선택된 대기 인원 ID: {self.selected_waiting_id}")
            if self.selected_slot_id is not None:
                status_lines.append(f"선택된 공대원 슬롯 ID: {self.selected_slot_id}")
            if self.selected_group_no is not None and self.selected_party_no is not None:
                status_lines.append(
                    f"선택된 대상 파티: {self.selected_group_no}공대 {self.selected_party_no}파티"
                )

            if status_lines:
                embed.add_field(
                    name="현재 선택 상태",
                    value="\n".join(status_lines),
                    inline=False,
                )

        await interaction.response.edit_message(embed=embed, view=self)


class WaitingToPartyButton(Button):
    def __init__(self):
        super().__init__(label="대기 인원 편입", style=discord.ButtonStyle.success, row=3)

    async def callback(self, interaction: discord.Interaction):
        view: PartyModifyView = self.view

        if view.selected_waiting_id is None:
            await interaction.response.send_message("대기 인원을 선택하세요.", ephemeral=True)
            return

        if view.selected_group_no is None or view.selected_party_no is None:
            await interaction.response.send_message("편입할 대상 파티를 선택하세요.", ephemeral=True)
            return

        try:
            result = view.party_modify_service.add_waiting_member_to_party(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                waiting_id=view.selected_waiting_id,
                group_no=view.selected_group_no,
                party_no=view.selected_party_no,
            )
        except Exception as e:
            await interaction.response.send_message(f"편입 실패: {e}", ephemeral=True)
            return

        active_result = view.party_manage_service.get_active_build_result(
            guild_id=view.rule.guild_id,
            channel_id=view.rule.channel_id,
        )
        embed = build_party_result_embed(active_result)
        embed.add_field(name="수정 결과", value=result.message, inline=False)

        await interaction.response.edit_message(embed=embed, view=view)


class RemoveToWaitingButton(Button):
    def __init__(self):
        super().__init__(label="공대원 제외", style=discord.ButtonStyle.danger, row=3)

    async def callback(self, interaction: discord.Interaction):
        view: PartyModifyView = self.view

        if view.selected_slot_id is None:
            await interaction.response.send_message("공대원을 선택하세요.", ephemeral=True)
            return

        try:
            result = view.party_modify_service.remove_party_member_to_waiting(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                slot_id=view.selected_slot_id,
            )
        except Exception as e:
            await interaction.response.send_message(f"제외 실패: {e}", ephemeral=True)
            return

        active_result = view.party_manage_service.get_active_build_result(
            guild_id=view.rule.guild_id,
            channel_id=view.rule.channel_id,
        )
        embed = build_party_result_embed(active_result)
        embed.add_field(name="수정 결과", value=result.message, inline=False)

        await interaction.response.edit_message(embed=embed, view=view)


class SwapWithWaitingButton(Button):
    def __init__(self):
        super().__init__(label="대기와 교체", style=discord.ButtonStyle.primary, row=3)

    async def callback(self, interaction: discord.Interaction):
        view: PartyModifyView = self.view

        if view.selected_waiting_id is None:
            await interaction.response.send_message("대기 인원을 선택하세요.", ephemeral=True)
            return

        if view.selected_slot_id is None:
            await interaction.response.send_message("교체할 공대원을 선택하세요.", ephemeral=True)
            return

        try:
            result = view.party_modify_service.swap_party_member_with_waiting(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                slot_id=view.selected_slot_id,
                waiting_id=view.selected_waiting_id,
            )
        except Exception as e:
            await interaction.response.send_message(f"교체 실패: {e}", ephemeral=True)
            return

        active_result = view.party_manage_service.get_active_build_result(
            guild_id=view.rule.guild_id,
            channel_id=view.rule.channel_id,
        )
        embed = build_party_result_embed(active_result)
        embed.add_field(name="수정 결과", value=result.message, inline=False)

        await interaction.response.edit_message(embed=embed, view=view)


class BackToResultButton(Button):
    def __init__(self):
        super().__init__(label="결과로 돌아가기", style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction):
        view: PartyModifyView = self.view

        active_result = view.party_manage_service.get_active_build_result(
            guild_id=view.rule.guild_id,
            channel_id=view.rule.channel_id,
        )
        if active_result is None:
            await interaction.response.send_message("현재 생성된 공대 결과가 없습니다.", ephemeral=True)
            return

        embed = build_party_result_embed(active_result)
        detail_view = PartyRuleDetailView(
            rule=view.rule,
            party_rule_service=view.party_rule_service,
            party_builder_service=view.party_builder_service,
            party_manage_service=view.party_manage_service,
            party_modify_service=view.party_modify_service,
        )
        await interaction.response.edit_message(embed=embed, view=detail_view)
