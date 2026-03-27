import discord
from discord.ui import View, Select, Button

# =========================
# EMBED BUILDERS (간단 버전)
# =========================

def build_empty_result_embed(raid_name: str, status_message: str | None = None):
    embed = discord.Embed(
        title=f"{raid_name} 공대 현황",
        description="아직 생성된 공대가 없습니다.",
    )

    if status_message:
        embed.add_field(name="\n\u200b안내", value=status_message, inline=False)

    return embed


def build_party_result_embed(result, status_message: str | None = None):
    if result is None:
        return build_empty_result_embed("레이드")

    desc = (
        f"총 신청자: {result.total_applicants}명\n"
        f"정식 공대 {result.full_group_count}개 / "
        f"상비군 {result.waiting_count}명\n\n"
    )

    for group in result.groups:
        desc += f"✨{group.group_no}공대\n"

        for party in group.parties:
            members = " / ".join(
                f"{m.character_name}({m.job[0]})" for m in party.members
            )
            desc += f"{party.party_no}-{members}\n"

        desc += "\n"


    embed = discord.Embed(
        title=f"{result.raid_name} 공대 현황",
        description=desc,
    )

    if status_message:
        embed.add_field(name="\n\u200b안내", value=status_message, inline=False)

    return embed


# =========================
# MAIN HOME VIEW
# =========================

class PartyBuildHomeView(View):
    def __init__(
        self,
        rule,
        party_builder_service,
        party_manage_service,
        party_modify_service,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service

    # =========================
    # 자동 생성
    # =========================
    @discord.ui.button(label="자동", style=discord.ButtonStyle.success, row=0)
    async def auto_build(self, interaction: discord.Interaction, button: Button):

        if self.party_manage_service.has_active_build(
            self.rule.guild_id, self.rule.channel_id
        ):
            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id, self.rule.channel_id
            )

            embed = build_party_result_embed(
                result,
                status_message="이미 생성된 공대가 있습니다. 초기화 후 진행해주세요.",
            )

            await interaction.response.edit_message(embed=embed, view=self)
            return

        loading = discord.Embed(title="공대 생성 중", description="데이터 조회 중...")
        await interaction.response.edit_message(embed=loading, view=None)

        try:
            await self.party_builder_service.build_parties(
                self.rule.guild_id,
                self.rule.channel_id,
                interaction.user.id,
            )

            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id, self.rule.channel_id
            )

            embed = build_party_result_embed(
                result,
                status_message="자동 생성 완료",
            )

        except Exception as e:
            embed = build_empty_result_embed(
                self.rule.raid_name,
                status_message=f"생성 실패: {e}",
            )

        await interaction.edit_original_response(embed=embed, view=self)

    # =========================
    # 수동 생성
    # =========================
    @discord.ui.button(label="수동", style=discord.ButtonStyle.primary, row=0)
    async def manual_build(self, interaction: discord.Interaction, button: Button):

        if self.party_manage_service.has_active_build(
            self.rule.guild_id, self.rule.channel_id
        ):
            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id, self.rule.channel_id
            )

            embed = build_party_result_embed(
                result,
                status_message="이미 생성된 공대가 있습니다. 초기화 후 진행해주세요.",
            )

            await interaction.response.edit_message(embed=embed, view=self)
            return

        loading = discord.Embed(title="수동 생성", description="데이터 조회 중...")
        await interaction.response.edit_message(embed=loading, view=None)

        try:
            await self.party_builder_service.build_empty_parties(
                self.rule.guild_id,
                self.rule.channel_id,
                interaction.user.id,
            )

            result = self.party_manage_service.get_active_build_result(
                self.rule.guild_id, self.rule.channel_id
            )

            embed = build_party_result_embed(
                result,
                status_message="수동 생성 완료 (수정으로 수동 배치하세요)",
            )

        except Exception as e:
            embed = build_empty_result_embed(
                self.rule.raid_name,
                status_message=f"생성 실패: {e}",
            )

        await interaction.edit_original_response(embed=embed, view=self)

    # =========================
    # 초기화
    # =========================
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

    # =========================
    # 수정
    # =========================
    @discord.ui.button(label="수정", style=discord.ButtonStyle.secondary, row=1)
    async def modify(self, interaction: discord.Interaction, button: Button):

        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id, self.rule.channel_id
        )

        if not result:
            embed = build_empty_result_embed(
                self.rule.raid_name,
                status_message="공대가 없습니다.",
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return

        view = PartyModifyGroupSelectView(
            self.rule,
            self.party_manage_service,
            self.party_modify_service,
        )

        embed = discord.Embed(title="수정할 공대를 선택하세요")

        await interaction.response.edit_message(embed=embed, view=view)

    # =========================
    # 공유
    # =========================
    @discord.ui.button(label="공유", style=discord.ButtonStyle.primary, row=1)
    async def share(self, interaction: discord.Interaction, button: Button):

        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id, self.rule.channel_id
        )

        if not result:
            await interaction.response.send_message("공대가 없습니다.", ephemeral=True)
            return

        embed = build_party_result_embed(result)

        await interaction.channel.send(embed=embed)

        await interaction.response.defer()

    # =========================
    # 닫기
    # =========================
    @discord.ui.button(label="닫기", style=discord.ButtonStyle.secondary, row=1)
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(view=None)


# =========================
# MODIFY VIEWS
# =========================

class PartyModifyHomeView(View):
    def __init__(
        self,
        rule,
        party_builder_service,
        party_manage_service,
        party_modify_service,
    ):
        super().__init__(timeout=300)

        self.rule = rule
        self.party_builder_service = party_builder_service
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service

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
                self.party_builder_service.build_parties,
                self.party_manage_service,
                self.party_modify_service,
            )
            await interaction.response.edit_message(embed=embed, view=home)
            return

        embed = discord.Embed(
            title="공대 선택",
            description="상비군으로 이동할 공대원을 고를 공대를 선택하세요.",
        )

        view = PartyModifyGroupSelectView(
            self.rule,
            self.party_manage_service,
            self.party_modify_service,
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
                self.party_builder_service.build_parties,
                self.party_manage_service,
                self.party_modify_service,
            )
            await interaction.response.edit_message(embed=embed, view=home)
            return

        embed = discord.Embed(
            title="상비군 선택",
            description="공대로 이동할 상비군 인원을 선택하세요.",
        )

        view = PartyModifyReserveView(
            self.rule,
            self.party_manage_service,
            self.party_modify_service,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="뒤로가기", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        result = self.party_manage_service.get_active_build_result(
            self.rule.guild_id,
            self.rule.channel_id,
        )

        if result:
            embed = build_party_result_embed(result)
        else:
            embed = build_empty_result_embed(self.rule.raid_name)

        home = PartyBuildHomeView(
            self.rule,
            self.party_builder_service.build_parties,
            self.party_manage_service,
            self.party_modify_service,
        )
        await interaction.response.edit_message(embed=embed, view=home)


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

        result = view.party_manage_service.get_active_build_result(
            view.rule.guild_id,
            view.rule.channel_id,
        )

        embed = discord.Embed(
            title=f"{group_no}공대 인원 선택",
            description="상비군으로 이동할 공대원을 선택하세요.",
        )

        next_view = PartyModifyGroupMemberView(
            view.rule,
            view.party_manage_service,
            view.party_modify_service,
            group_no,
        )

        await interaction.response.edit_message(embed=embed, view=next_view)


class PartyModifyGroupSelectView(View):
    def __init__(
        self,
        rule,
        party_manage_service,
        party_modify_service,
    ):
        super().__init__(timeout=300)
        self.rule = rule
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service

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
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
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
                slot_id=slot_id,
            )

            result = view.party_manage_service.get_active_build_result(
                view.rule.guild_id,
                view.rule.channel_id,
            )

            embed = build_party_result_embed(
                result,
                status_message=result_msg,
            )

            home = PartyBuildHomeView(
                view.rule,
                view.party_manage_service.party_builder_service,
                view.party_manage_service,
                view.party_modify_service,
            )
            await interaction.response.edit_message(embed=embed, view=home)

        except Exception as e:
            embed = discord.Embed(
                title=f"{view.group_no}공대 인원 선택",
                description=f"이동 실패: {e}",
            )
            await interaction.response.edit_message(embed=embed, view=view)


class PartyModifyGroupMemberView(View):
    def __init__(
        self,
        rule,
        party_manage_service,
        party_modify_service,
        group_no: int,
    ):
        super().__init__(timeout=300)
        self.rule = rule
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.group_no = group_no

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
            self.party_manage_service,
            self.party_modify_service,
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
            view.party_manage_service,
            view.party_modify_service,
            waiting_id,
            selected_name,
        )

        await interaction.response.edit_message(embed=embed, view=next_view)


class PartyModifyReserveView(View):
    def __init__(
        self,
        rule,
        party_manage_service,
        party_modify_service,
    ):
        super().__init__(timeout=300)
        self.rule = rule
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service

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
            self.party_builder_service,
            self.party_manage_service,
            self.party_modify_service,
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

        super().__init__(
            placeholder="이동할 공대/파티를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        group_no, party_no = self.values[0].split(":")
        group_no = int(group_no)
        party_no = int(party_no)

        try:
            result_msg = view.party_modify_service.add_waiting_member_to_party(
                guild_id=view.rule.guild_id,
                channel_id=view.rule.channel_id,
                waiting_id=view.waiting_id,
                group_no=group_no,
                party_no=party_no,
            )

            result = view.party_manage_service.get_active_build_result(
                view.rule.guild_id,
                view.rule.channel_id,
            )

            embed = build_party_result_embed(
                result,
                status_message=result_msg,
            )

            home = PartyBuildHomeView(
                view.rule,
                view.party_manage_service.party_builder_service,
                view.party_manage_service,
                view.party_modify_service,
            )
            await interaction.response.edit_message(embed=embed, view=home)

        except Exception as e:
            embed = discord.Embed(
                title="이동 대상 선택",
                description=f"이동 실패: {e}",
            )
            await interaction.response.edit_message(embed=embed, view=view)


class PartyMoveTargetSelectView(View):
    def __init__(
        self,
        rule,
        party_manage_service,
        party_modify_service,
        waiting_id: int,
        selected_member_name: str,
    ):
        super().__init__(timeout=300)
        self.rule = rule
        self.party_manage_service = party_manage_service
        self.party_modify_service = party_modify_service
        self.waiting_id = waiting_id
        self.selected_member_name = selected_member_name

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
            self.party_manage_service,
            self.party_modify_service,
        )
        await interaction.response.edit_message(embed=embed, view=view)
