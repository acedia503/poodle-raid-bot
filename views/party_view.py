import discord
from discord.ui import View, Select, Button

from utils.constants import JOB_OPTIONS


# =========================
# 공통 함수
# =========================

def get_job_short(job: str) -> str:
    return f"({job[0]})" if job else ""


def build_empty_result_embed(raid_name: str, status_message=None):
    embed = discord.Embed(
        title=f"{raid_name} 공대 현황",
        description="아직 생성된 공대가 없습니다.",
    )
    if status_message:
        embed.add_field(name="\n\u200b\n안내", value=status_message, inline=False)
    return embed


def build_party_result_embed(result, status_message=None):
    embed = discord.Embed(
        title=f"{result.raid_name} 공대 현황",
        description=(
            f"총 신청자: {result.total_applicants}명\n"
            f"정식 공대 {result.full_group_count}개 / 상비군 {result.waiting_count}명"
        ),
    )

    for group in result.groups:
        party1 = next((p for p in group.parties if p.party_no == 1), None)
        party2 = next((p for p in group.parties if p.party_no == 2), None)

        p1_power = party1.total_combat_power if party1 else 0
        p2_power = party2.total_combat_power if party2 else 0

        p1 = " / ".join(f"{m.character_name}{get_job_short(m.job)}" for m in (party1.members if party1 else []))
        p2 = " / ".join(f"{m.character_name}{get_job_short(m.job)}" for m in (party2.members if party2 else []))

        embed.add_field(
            name=f"✨{group.group_no}공대 - 총 전투력 [1파티] {p1_power:,} / [2파티] {p2_power:,}",
            value=f"1-{p1 or '비어있음'}\n2-{p2 or '비어있음'}\n\u200b",
            inline=False,
        )

    reserve = " / ".join(f"{m.character_name}{get_job_short(m.job)}" for m in result.waiting_members)

    embed.add_field(
        name="✨상비군",
        value=reserve or "없음",
        inline=False,
    )

    if status_message:
        embed.add_field(name="\n\u200b\n안내", value=status_message, inline=False)

    return embed


# =========================
# 메인 홈
# =========================

class PartyBuildHomeView(View):
    def __init__(self, rule, rule_service, builder, manage, modify):
        super().__init__(timeout=300)
        self.rule = rule
        self.rule_service = rule_service
        self.builder = builder
        self.manage = manage
        self.modify = modify

    @discord.ui.button(label="자동", style=discord.ButtonStyle.success)
    async def auto(self, interaction: discord.Interaction, _):
        if self.manage.has_active_build(self.rule.guild_id, self.rule.channel_id):
            result = self.manage.get_active_build_result(self.rule.guild_id, self.rule.channel_id)
            embed = build_party_result_embed(result, "이미 생성됨. 초기화 후 진행")
            return await interaction.response.edit_message(embed=embed, view=self)

        rule = self.rule_service.get_or_create_rule(
            self.rule.guild_id, self.rule.channel_id, self.rule.raid_name
        )

        embed = discord.Embed(title="자동 생성 규칙 설정")
        view = PartyAutoRuleEditView(rule, self.rule_service, self.builder, self.manage, self.modify)

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="수동", style=discord.ButtonStyle.primary)
    async def manual(self, interaction: discord.Interaction, _):
        await interaction.response.edit_message(embed=discord.Embed(title="생성중..."), view=None)

        await self.builder.build_empty_parties(
            self.rule.guild_id, self.rule.channel_id, interaction.user.id
        )

        result = self.manage.get_active_build_result(self.rule.guild_id, self.rule.channel_id)
        embed = build_party_result_embed(result, "수동 생성 완료")

        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="초기화", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, _):
        await self.manage.reset_build(self.rule.guild_id, self.rule.channel_id)
        embed = build_empty_result_embed(self.rule.raid_name, "초기화 완료")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="수정", style=discord.ButtonStyle.secondary, row=1)
    async def modify_btn(self, interaction: discord.Interaction, _):
        view = PartyModifyHomeView(
            self.rule, self.rule_service, self.builder, self.manage, self.modify
        )
        embed = discord.Embed(title="공대 수정", description="대상 선택")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=1)
    async def close(self, interaction: discord.Interaction, _):
        await interaction.response.edit_message(view=None)


# =========================
# 수정 홈
# =========================

class PartyModifyHomeView(View):
    def __init__(self, rule, rule_service, builder, manage, modify):
        super().__init__(timeout=300)
        self.rule = rule
        self.rule_service = rule_service
        self.builder = builder
        self.manage = manage
        self.modify = modify

    @discord.ui.button(label="공대 선택")
    async def group(self, interaction: discord.Interaction, _):
        view = PartyModifyGroupSelectView(
            self.rule, self.rule_service, self.builder, self.manage, self.modify
        )
        await interaction.response.edit_message(embed=discord.Embed(title="공대 선택"), view=view)

    @discord.ui.button(label="상비군 선택")
    async def reserve(self, interaction: discord.Interaction, _):
        view = PartyModifyReserveView(
            self.rule, self.rule_service, self.builder, self.manage, self.modify
        )
        await interaction.response.edit_message(embed=discord.Embed(title="상비군 선택"), view=view)

    @discord.ui.button(label="뒤로가기", row=1)
    async def back(self, interaction: discord.Interaction, _):
        result = self.manage.get_active_build_result(self.rule.guild_id, self.rule.channel_id)
        embed = build_party_result_embed(result) if result else build_empty_result_embed(self.rule.raid_name)

        home = PartyBuildHomeView(
            self.rule, self.rule_service, self.builder, self.manage, self.modify
        )
        await interaction.response.edit_message(embed=embed, view=home)


# =========================
# 공대 선택
# =========================

class PartyModifyGroupSelectView(View):
    def __init__(self, rule, rule_service, builder, manage, modify):
        super().__init__(timeout=300)
        self.rule = rule
        self.rule_service = rule_service
        self.builder = builder
        self.manage = manage
        self.modify = modify

        result = manage.get_active_build_result(rule.guild_id, rule.channel_id)
        groups = sorted({p.group_no for p in result.parties}) if result else []

        if groups:
            self.add_item(GroupSelect(groups))

    @discord.ui.button(label="뒤로가기", row=1)
    async def back(self, interaction, _):
        await interaction.response.edit_message(
            embed=discord.Embed(title="공대 수정"),
            view=PartyModifyHomeView(self.rule, self.rule_service, self.builder, self.manage, self.modify),
        )


class GroupSelect(Select):
    def __init__(self, groups):
        super().__init__(
            placeholder="공대 선택",
            options=[discord.SelectOption(label=f"{g}공대", value=str(g)) for g in groups],
        )

    async def callback(self, interaction):
        view = self.view
        group_no = int(self.values[0])

        next_view = PartyModifyGroupMemberView(
            view.rule, view.rule_service, view.builder, view.manage, view.modify, group_no
        )

        await interaction.response.edit_message(
            embed=discord.Embed(title=f"{group_no}공대 인원 선택"),
            view=next_view,
        )


# =========================
# 공대원 이동
# =========================

class PartyModifyGroupMemberView(View):
    def __init__(self, rule, rule_service, builder, manage, modify, group_no):
        super().__init__(timeout=300)
        self.rule = rule
        self.rule_service = rule_service
        self.builder = builder
        self.manage = manage
        self.modify = modify
        self.group_no = group_no

        result = manage.get_active_build_result(rule.guild_id, rule.channel_id)
        members = []

        if result:
            for p in result.parties:
                if p.group_no == group_no:
                    members.extend(p.members)

        self.add_item(GroupMemberSelect(members))

    @discord.ui.button(label="뒤로가기", row=1)
    async def back(self, interaction, _):
        await interaction.response.edit_message(
            embed=discord.Embed(title="공대 선택"),
            view=PartyModifyGroupSelectView(self.rule, self.rule_service, self.builder, self.manage, self.modify),
        )


class GroupMemberSelect(Select):
    def __init__(self, members):
        options = [
            discord.SelectOption(
                label=f"{m.character_name}{get_job_short(m.job)}",
                value=str(m.id),
            )
            for m in members[:25]
        ] or [discord.SelectOption(label="없음", value="none")]

        super().__init__(placeholder="공대원 선택", options=options)

    async def callback(self, interaction):
        view = self.view
        if self.values[0] == "none":
            return

        await view.modify.remove_party_member_to_waiting(
            view.rule.guild_id, view.rule.channel_id, int(self.values[0])
        )

        result = view.manage.get_active_build_result(view.rule.guild_id, view.rule.channel_id)

        home = PartyBuildHomeView(
            view.rule, view.rule_service, view.builder, view.manage, view.modify
        )

        await interaction.response.edit_message(embed=build_party_result_embed(result), view=home)
