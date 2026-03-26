# views/party_view.py

import discord
from discord.ui import View, Select, Button

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


def build_rule_edit_embed(
    party1_priority_jobs: list[str],
    party1_preferred_jobs: list[str],
    party2_priority_jobs: list[str],
    party2_preferred_jobs: list[str],
    status_message: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title="공대 생성 규칙 수정",
        description=(
            "각 파티에 우선 배치할 직업과 선호 직업을 설정해주세요.\n"
            "선호 직업은 필요한 경우에만 선택하면 됩니다.\n\n"
            "※ '없음'만 선택하면 비움 처리됩니다.\n"
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

    if status_message:
        embed.add_field(name="안내", value=status_message, inline=False)

    return embed


def build_build_home_embed(active_result, rule, status_message: str | None = None) -> discord.Embed:
    raid_name = getattr(active_result, "raid_name", None) or rule.raid_name

    if active_result is None:
        embed = discord.Embed(
            title=f"{raid_name} 공대 관리",
            description="현재 생성된 공대 결과가 없습니다.",
        )
    else:
        embed = discord.Embed(
            title=f"{raid_name} 공대 관리",
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


def build_party_result_embed(result, status_message: str | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=f"{result.raid_name} 공대 생성 결과",
        description=(
            f"총 신청자: {result.total_applicants}명\n"
            f"정식 공대 {result.full_group_count}개 / "
            f"임시 공대 {result.temp_group_count}개 / "
            f"대기 인원 {result.waiting_count}명"
        ),
    )

    # group_no 순서대로 출력
    groups: dict[int, list] = {}
    for party in result.parties:
        groups.setdefault(party.group_no, []).append(party)

    for group_no in sorted(groups.keys()):
        parties = sorted(groups[group_no], key=lambda p: p.party_no)
        lines = []

        for party in parties:
            lines.append(f"**{party.party_no}파티 (총 전투력: {party.total_combat_power:,})**")

            if not party.members:
                lines.append("배치 인원 없음")
                lines.append("")
                continue

            for idx, member in enumerate(party.members, start=1):
                slot_no = getattr(member, "slot_no", idx)
                lines.append(
                    f"{slot_no}. {member.character_name} ({member.job}) "
                    f"[{member.combat_power:,}]"
                )
            lines.append("")

        field_name = f"✨{group_no}공대"
        if any(getattr(party, "is_temp_group", False) for party in parties):
            field_name += " (임시)"

        embed.add_field(
            name=field_name,
            value="\n".join(lines).strip(),
            inline=False,
        )

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

    refresh_summary = getattr(result, "refresh_summary", None)
    if refresh_summary is not None:
        lines = [f"최신 정보 갱신 성공: {refresh_summary.updated_count}명"]
        if refresh_summary.failed_count > 0:
            lines.append(f"최신 정보 갱신 실패: {refresh_summary.failed_count}명")
            if refresh_summary.failed_characters:
                lines.append(
                    "실패 캐릭터: " + ", ".join(refresh_summary.failed_characters[:10])
                )
        embed.add_field(name="신청자 정보 갱신 결과", value="\n".join(lines), inline=False)

    if status_message:
        embed.add_field(name="안내", value=status_message, inline=False)

    return embed


def build_party_modify_embed(active_result, status_message: str | None = None) -> discord.Embed:
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

    if status_message:
        embed.add_field(name="안내", value=status_message, inline=False)

    return embed


class JobMultiSelect(Select):
    def __init__(self, placeholder: str, current_values: list[str], on_change_callback):
        options = []
        for job in JOB_OPTIONS:
            options.append(
                discord.SelectOption(
                    label=job,
                    value=job,
                    default=(job in current_values),
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

        if selected_values == ["없음"]:
            normalized_values = []
        else:
            normalized_values = []
            for value in selected_values:
                if value == "없음":
                    continue
                if value not in normalized_values:
                    normalized_values.append(value)

        await self.on_change_callback(interaction, normalized_values)


class SaveRuleButton(Button):
    def __init__(self):
        super().__init__(label="저장", style=discord.ButtonStyle.primary, row=4)

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

        home_view = PartyRuleHomeView(
            rule=updated_rule,
            party_rule_service=view.party_rule_service,
            party_builder_service=view.party_builder_service,
            party_manage_service=view.party_manage_service,
            party_modify_service=view.party_modify_service,
        )
        embed = build_rule_home_embed(updated_rule, status_message="규칙을 저장했습니다.")
        await interaction.response.edit_message(embed=embed, view=home_view)


class BackToRuleHomeButton(Button):
    def __init__(self):
        super().__init__(label="뒤로가기", style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        latest_rule = view.party_rule_service.get_or_create_rule(
            guild_id=view.rule.guild_id,
            channel_id=view.rule.channel_id,
            raid_name=view.rule.raid_name,
        )

        home_view = PartyRuleHomeView(
            rule=latest_rule,
            party_rule_service=view.party_rule_service,
            party_builder_service=view.party_builder_service,
            party_manage_service=view.party_manage_service,
            party_modify_service=view.party_modify_service,
        )
        embed = build_rule_home_embed(latest_rule)
        await interaction.response.edit_message(embed=embed, view=home_view)


class PartyRuleEditView(View):
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

        self.party1_priority_jobs = list(rule.party1_priority_jobs)
        self.party1_preferred_jobs = list(rule.party1_preferred_jobs)
        self.party2_priority_jobs = list(rule.party2_priority_jobs)
        self.party2_preferred_jobs = list(rule.party2_preferred_jobs)

        self.status_message: str | None = None
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
        self.add_item(BackToRuleHomeButton())

    async def _refresh(self, interaction: discord.Interaction):
        self._build_components()
        embed = build_rule_edit_embed(
            party1_priority_jobs=self.party1_priority_jobs,
            party1_preferred_jobs=self.party1_preferred_jobs,
            party2_priority_jobs=self.party2_priority_jobs,
            party2_preferred_jobs=self.party2_preferred_jobs,
            status_message=self.status_message,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_party1_priority_change(self, interaction: discord.Interaction, selected_values: list[str]):
        self.party1_priority_jobs = selected_values
        self.status_message = None
        await self._refresh(interaction)

    async def _on_party1_preferred_change(self, interaction: discord.Interaction, selected_values: list[str]):
        self.party1_preferred_jobs = selected_values
        self.status_message = None
        await self._refresh(interaction)

    async def _on_party2_priority_change(self, interaction: discord.Interaction, selected_values: list[str]):
        self.party2_priority_jobs = selected_values
        self.status_message = None
        await self._refresh(interaction)

    async def _on_party2_preferred_change(self, interaction: discord.Interaction, selected_values: list[str]):
        self.party2_preferred_jobs = selected_values
        self.status_message = None
        await self._refresh(interaction)


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
            self.rule.party1_priority_jobs,
            self.rule.party1_preferred_jobs,
            self.rule.party2_priority_jobs,
            self.rule.party2_preferred_jobs,
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
        embed = build_rule_home_embed(reset_rule, status_message="규칙을 초기화했습니다.")
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
                member_id = getattr(member, "id", None)
                if member_id is None and isinstance(member, dict):
                    member_id = member["id"]

                options.append(
                    discord.SelectOption(
                        label=f"{member.character_name} ({member.job})",
                        value=str(member_id),
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
        view = self.view
        if self.values[0] == "none":
            view.status_message = "선택 가능한 대기 인원이 없습니다."
            await view.refresh(interaction)
            return

        view.selected_waiting_id = int(self.values[0])
        view.status_message = None
        await view.refresh(interaction)


class PartySlotSelect(Select):
    def __init__(self, parties: list):
        options = []

        for party in parties:
            for idx, member in enumerate(party.members, start=1):
                slot_no = getattr(member, "slot_no", idx)
                slot_id = getattr(member, "id", None)
                if slot_id is None and isinstance(member, dict):
                    slot_id = member["id"]

                if slot_id is None:
                    continue

                options.append(
                    discord.SelectOption(
                        label=f"{party.group_no}공대 {party.party_no}파티 {slot_no}번 - {member.character_name}",
                        value=str(slot_id),
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
        view = self.view
        if self.values[0] == "none":
            view.status_message = "선택 가능한 공대원이 없습니다."
            await view.refresh(interaction)
            return

        view.selected_slot_id = int(self.values[0])
        view.status_message = None
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
            if getattr(party, "is_temp_group", False):
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
        view = self.view
        group_no, party_no = self.values[0].split(":")
        view.selected_group_no = int(group_no)
        view.selected_party_no = int(party_no)
        view.status_message = None
        await view.refresh(interaction)


class WaitingToPartyButton(Button):
    def __init__(self):
        super().__init__(label="대기 인원 편입", style=discord.ButtonStyle.success, row=3)

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if view.selected_waiting_id is None:
            view.status_message = "대기 인원을 먼저 선택하세요."
            await view.refresh(interaction)
            return

        if view.selected_group_no is None or view.selected_party_no is None:
            view.status_message = "편입할 대상 파티를 선택하세요."
            await view.refresh(interaction)
            return

        try:
            result = view.party_modify_service.add_waiting_member_to_party(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                waiting_id=view.selected_waiting_id,
                group_no=view.selected_group_no,
                party_no=view.selected_party_no,
            )
            active_result = view.party_manage_service.get_active_build_result(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
            )
            embed = build_party_result_embed(active_result, status_message=result.message)
            detail_view = PartyResultDetailView(
                rule=view.rule,
                party_rule_service=view.party_rule_service,
                party_builder_service=view.party_builder_service,
                party_manage_service=view.party_manage_service,
                party_modify_service=view.party_modify_service,
            )
            await interaction.response.edit_message(embed=embed, view=detail_view)
        except Exception as e:
            view.status_message = f"편입 실패: {e}"
            await view.refresh(interaction)


class RemoveToWaitingButton(Button):
    def __init__(self):
        super().__init__(label="공대원 제외", style=discord.ButtonStyle.danger, row=3)

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if view.selected_slot_id is None:
            view.status_message = "공대원을 먼저 선택하세요."
            await view.refresh(interaction)
            return

        try:
            result = view.party_modify_service.remove_party_member_to_waiting(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                slot_id=view.selected_slot_id,
            )
            active_result = view.party_manage_service.get_active_build_result(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
            )
            embed = build_party_result_embed(active_result, status_message=result.message)
            detail_view = PartyResultDetailView(
                rule=view.rule,
                party_rule_service=view.party_rule_service,
                party_builder_service=view.party_builder_service,
                party_manage_service=view.party_manage_service,
                party_modify_service=view.party_modify_service,
            )
            await interaction.response.edit_message(embed=embed, view=detail_view)
        except Exception as e:
            view.status_message = f"제외 실패: {e}"
            await view.refresh(interaction)


class SwapWithWaitingButton(Button):
    def __init__(self):
        super().__init__(label="대기와 교체", style=discord.ButtonStyle.primary, row=3)

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if view.selected_waiting_id is None:
            view.status_message = "대기 인원을 먼저 선택하세요."
            await view.refresh(interaction)
            return

        if view.selected_slot_id is None:
            view.status_message = "교체할 공대원을 먼저 선택하세요."
            await view.refresh(interaction)
            return

        try:
            result = view.party_modify_service.swap_party_member_with_waiting(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                slot_id=view.selected_slot_id,
                waiting_id=view.selected_waiting_id,
            )
            active_result = view.party_manage_service.get_active_build_result(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
            )
            embed = build_party_result_embed(active_result, status_message=result.message)
            detail_view = PartyResultDetailView(
                rule=view.rule,
                party_rule_service=view.party_rule_service,
                party_builder_service=view.party_builder_service,
                party_manage_service=view.party_manage_service,
                party_modify_service=view.party_modify_service,
            )
            await interaction.response.edit_message(embed=embed, view=detail_view)
        except Exception as e:
            view.status_message = f"교체 실패: {e}"
            await view.refresh(interaction)


class BackToBuildHomeButton(Button):
    def __init__(self):
        super().__init__(label="뒤로가기", style=discord.ButtonStyle.secondary, row=4)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        active_result = view.party_manage_service.get_active_build_result(
            guild_id=view.rule.guild_id,
            channel_id=view.rule.channel_id,
        )
        embed = build_build_home_embed(active_result, view.rule)
        build_view = PartyBuildHomeView(
            rule=view.rule,
            party_rule_service=view.party_rule_service,
            party_builder_service=view.party_builder_service,
            party_manage_service=view.party_manage_service,
            party_modify_service=view.party_modify_service,
        )
        await interaction.response.edit_message(embed=embed, view=build_view)


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
        self.status_message: str | None = None

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
            self.add_item(BackToBuildHomeButton())
            return

        self.add_item(WaitingMemberSelect(active_result.waiting_members))
        self.add_item(PartySlotSelect(active_result.parties))
        self.add_item(TargetPartySelect(active_result.parties))

        self.add_item(WaitingToPartyButton())
        self.add_item(RemoveToWaitingButton())
        self.add_item(SwapWithWaitingButton())
        self.add_item(BackToBuildHomeButton())

    async def refresh(self, interaction: discord.Interaction):
        self._build_components()
        active_result = self._get_active_result()

        if active_result is None:
            embed = discord.Embed(
                title="공대 수정",
                description="현재 생성된 공대 결과가 없습니다.",
            )
        else:
            embed = build_party_modify_embed(active_result, status_message=self.status_message)

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
                embed.add_field(name="현재 선택 상태", value="\n".join(status_lines), inline=False)

        await interaction.response.edit_message(embed=embed, view=self)


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
            embed = build_build_home_embed(None, self.rule, status_message="생성된 공대 결과가 없습니다.")
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
            embed = build_build_home_embed(active_result, self.rule, status_message="공대 생성을 완료했습니다.")
        except Exception as e:
            active_result = self.party_manage_service.get_active_build_result(
                guild_id=self.rule.guild_id,
                channel_id=self.rule.channel_id,
            )
            embed = build_build_home_embed(active_result, self.rule, status_message=f"공대 생성 실패: {e}")

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

        if reset_ok:
            status_message = "공대 결과를 초기화했습니다."
            active_result = None
        else:
            status_message = "초기화할 공대 결과가 없습니다."
            active_result = self.party_manage_service.get_active_build_result(
                guild_id=self.rule.guild_id,
                channel_id=self.rule.channel_id,
            )

        embed = build_build_home_embed(active_result, self.rule, status_message=status_message)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="공대 수정", style=discord.ButtonStyle.primary, row=1)
    async def modify_button(self, interaction: discord.Interaction, button: Button):
        active_result = self.party_manage_service.get_active_build_result(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
        )
        if active_result is None:
            embed = build_build_home_embed(None, self.rule, status_message="수정할 공대 결과가 없습니다.")
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
            embed = build_build_home_embed(None, self.rule, status_message="공유할 공대 결과가 없습니다.")
            await interaction.response.edit_message(embed=embed, view=self)
            return

        await interaction.channel.send(embed=build_party_result_embed(active_result))
        embed = build_build_home_embed(active_result, self.rule, status_message="공대 결과를 채널에 공유했습니다.")
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
