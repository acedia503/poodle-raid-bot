# views/party_view.py

import discord
from discord.ui import View, Select, Button

from utils.constants import JOB_OPTIONS


MAX_EMBED_DESC = 3500
MAX_DISCORD_MESSAGE = 1900


# =========================
# 공통 함수
# =========================

def get_job_short(job: str) -> str:
    return f"({job[0]})" if job else ""


def _job_short_text(job: str) -> str:
    return job[0] if job else ""


def _safe_get(obj, key, default=""):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def build_empty_result_embed(raid_name: str, status_message=None):
    embed = discord.Embed(
        title=f"🐾{raid_name} 공대 현황🐾",
        description="아직 생성된 공대가 없습니다.",
    )
    if status_message:
        embed.add_field(name="\n\u200b\n안내", value=status_message, inline=False)
    return embed


def _member_status_line(member, show_race_server: bool) -> str:
    user_name = _safe_get(member, "user_name", "")
    character_name = _safe_get(member, "character_name", "")
    race = _safe_get(member, "race", "")
    server = _safe_get(member, "server", "")
    job = _safe_get(member, "job", "")
    item_level = _safe_get(member, "item_level", "")
    combat_power = _safe_get(member, "combat_power", "")

    parts = [user_name, character_name]

    if show_race_server:
        parts.extend([race, server])

    parts.extend([
        job,
        f"{item_level}" if item_level != "" else "",
        f"{combat_power:,}" if isinstance(combat_power, int) else str(combat_power),
    ])

    return "/".join([p for p in parts if p != ""])


def _member_share_line(member, show_race_server: bool) -> str:
    user_name = _safe_get(member, "user_name", "")
    character_name = _safe_get(member, "character_name", "")
    race = _safe_get(member, "race", "")
    server = _safe_get(member, "server", "")
    job = _safe_get(member, "job", "")

    if show_race_server:
        parts = [user_name, character_name, race, server, job]
        return "/".join([p for p in parts if p != ""])

    return f"{character_name}({_job_short_text(job)})"


def _build_status_group_block(group, show_race_server: bool) -> str:
    party1 = next((p for p in group.parties if p.party_no == 1), None)
    party2 = next((p for p in group.parties if p.party_no == 2), None)

    p1_power = party1.total_combat_power if party1 else 0
    p2_power = party2.total_combat_power if party2 else 0

    lines = [f"✨{group.group_no}공대"]

    lines.append(f"[1파티] 총 전투력: {p1_power:,}")
    if party1 and party1.members:
        for idx, member in enumerate(party1.members, start=1):
            lines.append(f"{idx} - {_member_status_line(member, show_race_server)}")
    else:
        lines.append("비어있음")

    lines.append("")
    lines.append(f"[2파티] 총 전투력: {p2_power:,}")
    if party2 and party2.members:
        for idx, member in enumerate(party2.members, start=1):
            lines.append(f"{idx} - {_member_status_line(member, show_race_server)}")
    else:
        lines.append("비어있음")

    return "\n".join(lines)


def _build_share_group_block(group, show_race_server: bool) -> str:
    party1 = next((p for p in group.parties if p.party_no == 1), None)
    party2 = next((p for p in group.parties if p.party_no == 2), None)

    p1_power = party1.total_combat_power if party1 else 0
    p2_power = party2.total_combat_power if party2 else 0

    lines = [f"✨{group.group_no}공대"]

    if show_race_server:
        lines.append(f"[1파티] 총 전투력: {p1_power:,}")
        if party1 and party1.members:
            for idx, member in enumerate(party1.members, start=1):
                lines.append(f"{idx} - {_member_share_line(member, True)}")
        else:
            lines.append("비어있음")

        lines.append("")
        lines.append(f"[2파티] 총 전투력: {p2_power:,}")
        if party2 and party2.members:
            for idx, member in enumerate(party2.members, start=1):
                lines.append(f"{idx} - {_member_share_line(member, True)}")
        else:
            lines.append("비어있음")
    else:
        p1_text = "/".join(
            [_member_share_line(m, False) for m in (party1.members if party1 else [])]
        ) or "비어있음"
        p2_text = "/".join(
            [_member_share_line(m, False) for m in (party2.members if party2 else [])]
        ) or "비어있음"

        lines.append(f"1 - {p1_text}")
        lines.append(f"2 - {p2_text}")

    return "\n".join(lines)


def _split_embeds_by_group(title: str, header_lines: list[str], group_blocks: list[str]) -> list[discord.Embed]:
    embeds = []
    current_desc = "\n".join(header_lines).strip()

    for block in group_blocks:
        candidate = f"{current_desc}\n\n{block}" if current_desc else block

        if len(candidate) > MAX_EMBED_DESC:
            embeds.append(discord.Embed(title=title, description=current_desc))
            current_desc = block
        else:
            current_desc = candidate

    if current_desc:
        embeds.append(discord.Embed(title=title, description=current_desc))

    return embeds


def build_party_status_embeds(result, show_race_server: bool, status_message: str | None = None):
    title = f"🐾{result.raid_name} 공대 현황🐾"

    header_lines = []
    if status_message:
        header_lines.append(f"안내: {status_message}")

    group_blocks = [
        _build_status_group_block(group, show_race_server)
        for group in result.groups
    ]

    reserve_lines = ["✨상비군"]
    if result.waiting_members:
        for idx, member in enumerate(result.waiting_members, start=1):
            reserve_lines.append(f"{idx} - {_member_status_line(member, show_race_server)}")
    else:
        reserve_lines.append("없음")

    group_blocks.append("\n".join(reserve_lines))
    return _split_embeds_by_group(title, header_lines, group_blocks)


def build_party_share_embeds(result, show_race_server: bool):
    title = f"🐾{result.raid_name} 공대 공유🐾"

    group_blocks = [
        _build_share_group_block(group, show_race_server)
        for group in result.groups
    ]

    return _split_embeds_by_group(title, [], group_blocks)


def _build_share_group_text(group, show_race_server: bool) -> str:
    party1 = next((p for p in group.parties if p.party_no == 1), None)
    party2 = next((p for p in group.parties if p.party_no == 2), None)

    p1_power = party1.total_combat_power if party1 else 0
    p2_power = party2.total_combat_power if party2 else 0

    lines = [f"✨{group.group_no}공대"]

    if show_race_server:
        lines.append(f"[1파티] 총 전투력: {p1_power:,}")
        if party1 and party1.members:
            for idx, member in enumerate(party1.members, start=1):
                lines.append(f"{idx} - {_member_share_line(member, True)}")
        else:
            lines.append("비어있음")

        lines.append("")
        lines.append(f"[2파티] 총 전투력: {p2_power:,}")
        if party2 and party2.members:
            for idx, member in enumerate(party2.members, start=1):
                lines.append(f"{idx} - {_member_share_line(member, True)}")
        else:
            lines.append("비어있음")
    else:
        p1_text = "/".join(
            [_member_share_line(m, False) for m in (party1.members if party1 else [])]
        ) or "비어있음"
        p2_text = "/".join(
            [_member_share_line(m, False) for m in (party2.members if party2 else [])]
        ) or "비어있음"

        lines.append(f"1 - {p1_text}")
        lines.append(f"2 - {p2_text}")

    return "\n".join(lines)


def _build_share_reserve_block(result, show_race_server: bool) -> str:
    lines = ["✨상비군"]

    if result.waiting_members:
        if show_race_server:
            for idx, member in enumerate(result.waiting_members, start=1):
                lines.append(f"{idx} - {_member_share_line(member, True)}")
        else:
            reserve_text = "/".join(
                [_member_share_line(member, False) for member in result.waiting_members]
            ) or "없음"
            lines.append(reserve_text)
    else:
        lines.append("없음")

    return "\n".join(lines)
    

def _split_text_chunks(blocks: list[str], title: str) -> list[str]:
    chunks = []
    current = title.strip()

    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block

        if len(candidate) > MAX_DISCORD_MESSAGE:
            chunks.append(current)
            current = block
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks


def build_party_share_text_chunks(result, show_race_server: bool) -> list[str]:
    title = f"🐾{result.raid_name} 공대 공유🐾"

    blocks = [
        _build_share_group_text(group, show_race_server)
        for group in result.groups
    ]

    blocks.append(_build_share_reserve_block(result, show_race_server))

    return _split_text_chunks(blocks, title)


def build_first_status_embed(result, show_race_server: bool, status_message: str | None = None):
    embeds = build_party_status_embeds(
        result,
        show_race_server=show_race_server,
        status_message=status_message,
    )
    return embeds[0] if embeds else build_empty_result_embed(result.raid_name, status_message)


# 기존 코드와의 호환용
def build_party_result_embed(result, status_message=None, show_race_server: bool = True):
    if result is None:
        return build_empty_result_embed("레이드", status_message)
    return build_first_status_embed(result, show_race_server, status_message)


def build_rule_edit_embed(
    rule,
    party1_priority_jobs: list[str],
    party1_preferred_jobs: list[str],
    party2_priority_jobs: list[str],
    party2_preferred_jobs: list[str],
    status_message: str | None = None,
):
    embed = discord.Embed(
        title="자동 생성 규칙 설정",
        description=(
            "각 파티의 우선 직업과 선호 직업을 설정한 뒤 생성하세요.\n"
            "자동 생성 시에만 이 규칙이 반영됩니다."
        ),
    )

    embed.add_field(
        name="1파티",
        value=(
            f"우선 직업: {', '.join(party1_priority_jobs) if party1_priority_jobs else '없음'}\n"
            f"선호 직업: {', '.join(party1_preferred_jobs) if party1_preferred_jobs else '없음'}"
        ),
        inline=False,
    )

    embed.add_field(
        name="2파티",
        value=(
            f"우선 직업: {', '.join(party2_priority_jobs) if party2_priority_jobs else '없음'}\n"
            f"선호 직업: {', '.join(party2_preferred_jobs) if party2_preferred_jobs else '없음'}"
        ),
        inline=False,
    )

    if status_message:
        embed.add_field(name="\n\u200b\n안내", value=status_message, inline=False)

    return embed


# =========================
# 메인 홈
# =========================

class PartyBuildHomeView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
        show_race_server: bool = True,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.show_race_server = show_race_server

    @discord.ui.button(label="자동", style=discord.ButtonStyle.success, row=0)
    async def auto_build(self, interaction: discord.Interaction, button: Button):
        if self.party_manage_service.has_active_build(
            self.rule.guild_id,
            self.rule.channel_id,
        ):
            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id,
                self.rule.channel_id,
            )

            embed = build_first_status_embed(
                result,
                show_race_server=self.show_race_server,
                status_message="이미 생성된 공대가 있습니다. 초기화 후 진행해주세요.",
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return

        latest_rule = self.party_rule_service.get_or_create_rule(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
            raid_name=self.rule.raid_name,
        )

        embed = build_rule_edit_embed(
            latest_rule,
            latest_rule.party1_priority_jobs,
            latest_rule.party1_preferred_jobs,
            latest_rule.party2_priority_jobs,
            latest_rule.party2_preferred_jobs,
        )

        view = PartyAutoRuleEditView(
            rule=latest_rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
            show_race_server=self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="수동", style=discord.ButtonStyle.primary, row=0)
    async def manual_build(self, interaction: discord.Interaction, button: Button):
        if self.party_manage_service.has_active_build(
            self.rule.guild_id,
            self.rule.channel_id,
        ):
            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id,
                self.rule.channel_id,
            )

            embed = build_first_status_embed(
                result,
                show_race_server=self.show_race_server,
                status_message="이미 생성된 공대가 있습니다. 초기화 후 진행해주세요.",
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return

        loading = discord.Embed(
            title="수동 생성",
            description="데이터 조회 중...",
        )
        await interaction.response.edit_message(embed=loading, view=None)

        try:
            await self.party_builder_service.build_empty_parties(
                self.rule.guild_id,
                self.rule.channel_id,
                interaction.user.id,
            )

            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id,
                self.rule.channel_id,
            )

            embed = build_first_status_embed(
                result,
                show_race_server=self.show_race_server,
                status_message="수동 생성 완료 (수정으로 수동 배치하세요)",
            )

        except Exception as e:
            embed = build_empty_result_embed(
                self.rule.raid_name,
                status_message=f"생성 실패: {e}",
            )

        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="초기화", style=discord.ButtonStyle.danger, row=0)
    async def reset(self, interaction: discord.Interaction, button: Button):
        await self.party_manage_service.reset_build(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        embed = build_empty_result_embed(
            self.rule.raid_name,
            status_message="초기화 완료",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="수정", style=discord.ButtonStyle.secondary, row=1)
    async def modify(self, interaction: discord.Interaction, button: Button):
        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        if not result:
            embed = build_empty_result_embed(
                self.rule.raid_name,
                status_message="공대가 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return

        view = PartyModifyHomeView(
            self.rule,
            self.party_rule_service,
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
            self.show_race_server,
        )

        embed = discord.Embed(
            title="공대 수정",
            description="수정할 대상을 선택하세요.",
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="공유", style=discord.ButtonStyle.primary, row=1)
    async def share(self, interaction: discord.Interaction, button: Button):
        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )
    
        if not result:
            embed = build_empty_result_embed(
                self.rule.raid_name,
                status_message="공대가 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
    
        text_chunks = build_party_share_text_chunks(
            result,
            show_race_server=self.show_race_server,
        )
    
        if not text_chunks:
            await interaction.response.send_message(
                "복사할 공유 내용이 없습니다.",
                ephemeral=True,
            )
            return
    
        await interaction.response.send_message(
            text_chunks[0],
            ephemeral=True,
        )
    
        for chunk in text_chunks[1:]:
            await interaction.followup.send(
                chunk,
                ephemeral=True,
            )

    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(view=None)


# =========================
# 수정 홈
# =========================

class PartyModifyHomeView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
        show_race_server: bool = True,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.show_race_server = show_race_server

    @discord.ui.button(label="공대 선택", style=discord.ButtonStyle.primary, row=0)
    async def select_group(self, interaction: discord.Interaction, button: Button):
        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        if not result:
            embed = build_empty_result_embed(
                self.rule.raid_name,
                status_message="공대가 없습니다.",
            )
            home = PartyBuildHomeView(
                self.rule,
                self.party_rule_service,
                self.party_builder_service,
                self.party_manage_service,
                self.party_modify_service,
                self.show_race_server,
            )
            await interaction.response.edit_message(embed=embed, view=home)
            return

        embed = discord.Embed(
            title="공대 선택",
            description="상비군으로 이동할 공대원을 고를 공대를 선택하세요.",
        )

        view = PartyModifyGroupSelectView(
            self.rule,
            self.party_rule_service,
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
            self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="상비군 선택", style=discord.ButtonStyle.success, row=0)
    async def select_reserve(self, interaction: discord.Interaction, button: Button):
        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        if not result:
            embed = build_empty_result_embed(
                self.rule.raid_name,
                status_message="공대가 없습니다.",
            )
            home = PartyBuildHomeView(
                self.rule,
                self.party_rule_service,
                self.party_builder_service,
                self.party_manage_service,
                self.party_modify_service,
                self.show_race_server,
            )
            await interaction.response.edit_message(embed=embed, view=home)
            return

        embed = discord.Embed(
            title="상비군 선택",
            description="공대로 이동할 상비군 인원을 선택하세요.",
        )

        view = PartyModifyReserveView(
            self.rule,
            self.party_rule_service,
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
            self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="뒤로가기", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        if result:
            embed = build_first_status_embed(
                result,
                show_race_server=self.show_race_server,
            )
        else:
            embed = build_empty_result_embed(self.rule.raid_name)

        home = PartyBuildHomeView(
            self.rule,
            self.party_rule_service,
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
            self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=home)


# =========================
# 공대 선택
# =========================

class PartyModifyGroupSelectView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
        show_race_server: bool = True,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.show_race_server = show_race_server

        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        groups = []
        if result:
            groups = sorted({party.group_no for party in result.parties})

        if groups:
            self.add_item(GroupSelect(groups))

    @discord.ui.button(label="뒤로가기", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="공대 수정",
            description="수정할 대상을 선택하세요.",
        )

        view = PartyModifyHomeView(
            self.rule,
            self.party_rule_service,
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
            self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class GroupSelect(Select):
    def __init__(self, groups: list[int]):
        options = [
            discord.SelectOption(label=f"{group_no}공대", value=str(group_no))
            for group_no in groups[:25]
        ]

        super().__init__(
            placeholder="공대를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        group_no = int(self.values[0])

        embed = discord.Embed(
            title=f"{group_no}공대 인원 선택",
            description="상비군으로 이동할 공대원을 선택하세요.",
        )

        next_view = PartyModifyGroupMemberView(
            view.rule,
            view.party_rule_service,
            view.party_builder_service,
            view.party_manage_service,
            view.party_modify_service,
            group_no,
            view.show_race_server,
        )

        await interaction.response.edit_message(embed=embed, view=next_view)


# =========================
# 공대원 이동
# =========================

class PartyModifyGroupMemberView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
        group_no: int,
        show_race_server: bool = True,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.group_no = group_no
        self.show_race_server = show_race_server

        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        members = []
        if result:
            parties = [p for p in result.parties if p.group_no == group_no]
            for party in sorted(parties, key=lambda p: p.party_no):
                members.extend(party.members)

        self.add_item(GroupMemberSelect(members))

    @discord.ui.button(label="뒤로가기", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="공대 선택",
            description="상비군으로 이동할 공대원을 고를 공대를 선택하세요.",
        )

        view = PartyModifyGroupSelectView(
            self.rule,
            self.party_rule_service,
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
            self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class GroupMemberSelect(Select):
    def __init__(self, members: list):
        options = []

        for member in members[:25]:
            options.append(
                discord.SelectOption(
                    label=f"{member.character_name}{get_job_short(member.job)}",
                    value=str(member.id),
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
            placeholder="상비군으로 이동할 공대원을 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if self.values[0] == "none":
            embed = discord.Embed(
                title=f"{view.group_no}공대 인원 선택",
                description="선택 가능한 공대원이 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=view)
            return

        slot_id = int(self.values[0])

        try:
            result_msg = view.party_modify_service.remove_party_member_to_waiting(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                raid_name=view.rule.raid_name,
                slot_id=slot_id,
            )

            result = view.party_manage_service.get_active_build_result(
                view.rule.guild_id,
                view.rule.channel_id,
            )

            embed = build_first_status_embed(
                result,
                show_race_server=view.show_race_server,
                status_message=result_msg,
            )

            home = PartyBuildHomeView(
                view.rule,
                view.party_rule_service,
                view.party_builder_service,
                view.party_manage_service,
                view.party_modify_service,
                view.show_race_server,
            )
            await interaction.response.edit_message(embed=embed, view=home)

        except Exception as e:
            embed = discord.Embed(
                title=f"{view.group_no}공대 인원 선택",
                description=f"이동 실패: {e}",
            )
            await interaction.response.edit_message(embed=embed, view=view)


# =========================
# 상비군 이동
# =========================

class PartyModifyReserveView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
        show_race_server: bool = True,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.show_race_server = show_race_server

        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        waiting_members = result.waiting_members if result else []
        self.add_item(ReserveMemberSelect(waiting_members))

    @discord.ui.button(label="뒤로가기", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="공대 수정",
            description="수정할 대상을 선택하세요.",
        )
        view = PartyModifyHomeView(
            self.rule,
            self.party_rule_service,
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
            self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class ReserveMemberSelect(Select):
    def __init__(self, waiting_members: list):
        options = []

        for member in waiting_members[:25]:
            options.append(
                discord.SelectOption(
                    label=f"{member.character_name}{get_job_short(member.job)}",
                    value=str(member.id),
                    description=f"{member.job} / {member.combat_power:,}",
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="상비군 없음",
                    value="none",
                    description="선택 가능한 상비군이 없습니다.",
                )
            )
            disabled = True
        else:
            disabled = False

        super().__init__(
            placeholder="공대로 이동할 상비군 인원을 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if self.values[0] == "none":
            embed = discord.Embed(
                title="상비군 선택",
                description="선택 가능한 상비군이 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=view)
            return

        waiting_id = int(self.values[0])

        result = view.party_manage_service.get_active_build_result(
            view.rule.guild_id,
            view.rule.channel_id,
        )

        selected_name = "상비군"
        if result:
            target = next((m for m in result.waiting_members if m.id == waiting_id), None)
            if target:
                selected_name = target.character_name

        embed = discord.Embed(
            title="이동 대상 선택",
            description=f"선택한 인원: {selected_name}\n이동할 공대/파티를 선택하세요.",
        )

        next_view = PartyMoveTargetSelectView(
            view.rule,
            view.party_rule_service,
            view.party_builder_service,
            view.party_manage_service,
            view.party_modify_service,
            waiting_id,
            selected_name,
            view.show_race_server,
        )

        await interaction.response.edit_message(embed=embed, view=next_view)


class PartyMoveTargetSelectView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
        waiting_id: int,
        selected_member_name: str,
        show_race_server: bool = True,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.waiting_id = waiting_id
        self.selected_member_name = selected_member_name
        self.show_race_server = show_race_server

        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        parties = result.parties if result else []
        self.add_item(MoveTargetSelect(parties))

    @discord.ui.button(label="뒤로가기", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="상비군 선택",
            description="공대로 이동할 상비군 인원을 선택하세요.",
        )
        view = PartyModifyReserveView(
            self.rule,
            self.party_rule_service,
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
            self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class MoveTargetSelect(Select):
    def __init__(self, parties: list):
        options = []

        for party in sorted(parties, key=lambda p: (p.group_no, p.party_no))[:25]:
            options.append(
                discord.SelectOption(
                    label=f"{party.group_no}공대 {party.party_no}파티",
                    value=f"{party.group_no}:{party.party_no}",
                    description=f"현재 인원 {len(party.members)}명",
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="이동 대상 없음",
                    value="none",
                    description="이동 가능한 공대/파티가 없습니다.",
                )
            )
            disabled = True
        else:
            disabled = False

        super().__init__(
            placeholder="이동할 공대/파티를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if self.values[0] == "none":
            embed = discord.Embed(
                title="이동 대상 선택",
                description="이동 가능한 공대/파티가 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=view)
            return

        group_no, party_no = self.values[0].split(":")
        group_no = int(group_no)
        party_no = int(party_no)

        try:
            result_msg = view.party_modify_service.add_waiting_member_to_party(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                raid_name=view.rule.raid_name,
                waiting_id=view.waiting_id,
                group_no=group_no,
                party_no=party_no,
            )

            result = view.party_manage_service.get_active_build_result(
                view.rule.guild_id,
                view.rule.channel_id,
            )

            embed = build_first_status_embed(
                result,
                show_race_server=view.show_race_server,
                status_message=result_msg,
            )

            home = PartyBuildHomeView(
                view.rule,
                view.party_rule_service,
                view.party_builder_service,
                view.party_manage_service,
                view.party_modify_service,
                view.show_race_server,
            )
            await interaction.response.edit_message(embed=embed, view=home)

        except Exception as e:
            embed = discord.Embed(
                title="이동 대상 선택",
                description=f"이동 실패: {e}",
            )
            await interaction.response.edit_message(embed=embed, view=view)


# =========================
# 자동 생성 규칙 설정
# =========================

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
            min_values=0,
            max_values=len(JOB_OPTIONS),
            options=options,
        )
        self.on_change_callback = on_change_callback

    async def callback(self, interaction: discord.Interaction):
        selected_values = list(self.values)

        normalized_values = []
        for value in selected_values:
            if value not in normalized_values:
                normalized_values.append(value)

        await self.on_change_callback(interaction, normalized_values)


class PartyAutoRuleEditView(View):
    def __init__(
        self,
        rule,
        party_rule_service,
        party_builder_service,
        party_manage_service,
        party_modify_service,
        show_race_server: bool = True,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_rule_service = party_rule_service
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.show_race_server = show_race_server

        self.party1_priority_jobs = list(rule.party1_priority_jobs)
        self.party1_preferred_jobs = list(rule.party1_preferred_jobs)
        self.party2_priority_jobs = list(rule.party2_priority_jobs)
        self.party2_preferred_jobs = list(rule.party2_preferred_jobs)

        self.add_item(
            JobMultiSelect(
                "1파티 우선 직업 선택",
                self.party1_priority_jobs,
                self._on_party1_priority_change,
            )
        )
        self.add_item(
            JobMultiSelect(
                "1파티 선호 직업 선택",
                self.party1_preferred_jobs,
                self._on_party1_preferred_change,
            )
        )
        self.add_item(
            JobMultiSelect(
                "2파티 우선 직업 선택",
                self.party2_priority_jobs,
                self._on_party2_priority_change,
            )
        )
        self.add_item(
            JobMultiSelect(
                "2파티 선호 직업 선택",
                self.party2_preferred_jobs,
                self._on_party2_preferred_change,
            )
        )

    def _normalize_jobs(self, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            if value not in normalized:
                normalized.append(value)
        return normalized

    async def _refresh(
        self,
        interaction: discord.Interaction,
        status_message: str | None = None,
    ):
        embed = build_rule_edit_embed(
            self.rule,
            self.party1_priority_jobs,
            self.party1_preferred_jobs,
            self.party2_priority_jobs,
            self.party2_preferred_jobs,
            status_message=status_message,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _on_party1_priority_change(self, interaction, selected_values):
        self.party1_priority_jobs = self._normalize_jobs(selected_values)
        await self._refresh(interaction)

    async def _on_party1_preferred_change(self, interaction, selected_values):
        self.party1_preferred_jobs = self._normalize_jobs(selected_values)
        await self._refresh(interaction)

    async def _on_party2_priority_change(self, interaction, selected_values):
        self.party2_priority_jobs = self._normalize_jobs(selected_values)
        await self._refresh(interaction)

    async def _on_party2_preferred_change(self, interaction, selected_values):
        self.party2_preferred_jobs = self._normalize_jobs(selected_values)
        await self._refresh(interaction)

    @discord.ui.button(label="생성", style=discord.ButtonStyle.success, row=4)
    async def generate_button(self, interaction: discord.Interaction, button: Button):
        party1_priority = self._normalize_jobs(self.party1_priority_jobs)
        party1_preferred = self._normalize_jobs(self.party1_preferred_jobs)
        party2_priority = self._normalize_jobs(self.party2_priority_jobs)
        party2_preferred = self._normalize_jobs(self.party2_preferred_jobs)

        self.party_rule_service.update_rule(
            guild_id=self.rule.guild_id,
            channel_id=self.rule.channel_id,
            raid_name=self.rule.raid_name,
            party1_priority_jobs=party1_priority,
            party1_preferred_jobs=party1_preferred,
            party2_priority_jobs=party2_priority,
            party2_preferred_jobs=party2_preferred,
        )

        loading_embed = discord.Embed(
            title="공대 생성 중",
            description="규칙 저장 후 신청자 정보를 조회하고 있습니다.",
        )
        await interaction.response.edit_message(embed=loading_embed, view=None)

        try:
            await self.party_builder_service.build_parties(
                guild_id=self.rule.guild_id,
                channel_id=self.rule.channel_id,
                created_by=interaction.user.id,
            )

            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id,
                self.rule.channel_id,
            )

            embed = build_first_status_embed(
                result,
                show_race_server=self.show_race_server,
                status_message="자동 생성 완료",
            )

        except Exception as e:
            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id,
                self.rule.channel_id,
            )

            if result:
                embed = build_first_status_embed(
                    result,
                    show_race_server=self.show_race_server,
                    status_message=f"생성 실패: {e}",
                )
            else:
                embed = build_empty_result_embed(
                    self.rule.raid_name,
                    status_message=f"생성 실패: {e}",
                )

        view = PartyBuildHomeView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
            show_race_server=self.show_race_server,
        )
        await interaction.edit_original_response(embed=embed, view=view)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=4)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        embed = (
            build_first_status_embed(result, self.show_race_server)
            if result
            else build_empty_result_embed(self.rule.raid_name)
        )

        view = PartyBuildHomeView(
            rule=self.rule,
            party_rule_service=self.party_rule_service,
            party_builder_service=self.party_builder_service,
            party_manage_service=self.party_manage_service,
            party_modify_service=self.party_modify_service,
            show_race_server=self.show_race_server,
        )
        await interaction.response.edit_message(embed=embed, view=view)
