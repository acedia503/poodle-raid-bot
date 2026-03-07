# views.py
# Discord UI(View) 모음

import logging
import discord
from discord import SelectOption

from storage import (
    save_active_raids,
    clear_saved_parties,
    load_generated_parties,
    save_generated_parties,
)
from ui_helpers import make_simple_embed
from party_helpers import (
    find_member_in_saved_parties,
    remove_member_from_saved_parties,
)


class DeleteRaidConfirmView(discord.ui.View):
    def __init__(
        self,
        raid_name: str,
        requester_id: int,
        active_raids: dict,
    ):
        super().__init__(timeout=60)
        self.raid_name = raid_name
        self.requester_id = requester_id
        self.active_raids = active_raids

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "이 삭제 확인 버튼은 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="삭제", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.raid_name not in self.active_raids:
            embed = make_simple_embed(
                title="⚠️ 이미 삭제되었거나 존재하지 않는 레이드입니다."
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        member_count = len(self.active_raids[self.raid_name]["members"])

        del self.active_raids[self.raid_name]
        save_active_raids(self.active_raids)

        embed = make_simple_embed(
            title="🗑️ 레이드 삭제 완료",
            description=(
                f"레이드: **{self.raid_name}**\n"
                f"삭제된 신청자 수: **{member_count}명**"
            )
        )

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = make_simple_embed(
            title="✅ 레이드 삭제가 취소되었습니다.",
            description=f"레이드: **{self.raid_name}**"
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ClearPartyConfirmView(discord.ui.View):
    def __init__(self, raid_name: str, requester_id: int):
        super().__init__(timeout=60)
        self.raid_name = raid_name
        self.requester_id = requester_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "이 버튼은 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="공대초기화", style=discord.ButtonStyle.danger)
    async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            raids, waiting_members, excluded_members = load_generated_parties(self.raid_name)

            if not raids and not waiting_members and not excluded_members:
                embed = make_simple_embed(
                    title="⚠️ 초기화할 공대 정보가 없습니다.",
                    description=f"레이드: **{self.raid_name}**"
                )
                await interaction.response.edit_message(embed=embed, view=None)
                return

            total_party_members = sum(len(r["party1"]) + len(r["party2"]) for r in raids)
            total_waiting = len(waiting_members)
            total_excluded = len(excluded_members)

            clear_saved_parties(self.raid_name)

            embed = make_simple_embed(
                title="🧹 공대 초기화 완료",
                description=(
                    f"레이드: **{self.raid_name}**\n"
                    f"삭제된 공대원 수: **{total_party_members}명**\n"
                    f"삭제된 대기 인원 수: **{total_waiting}명**\n"
                    f"삭제된 제외 인원 수: **{total_excluded}명**\n\n"
                    f"신청목록은 유지됩니다."
                )
            )
            await interaction.response.edit_message(embed=embed, view=None)

        except Exception:
            logging.exception("공대초기화 실패")
            embed = make_simple_embed(
                title="❌ 공대 초기화 실패",
                description="공대 초기화 중 오류가 발생했습니다."
            )
            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = make_simple_embed(
            title="✅ 공대 초기화가 취소되었습니다.",
            description=f"레이드: **{self.raid_name}**"
        )
        await interaction.response.edit_message(embed=embed, view=None)


class FullPartyResolveView(discord.ui.View):
    def __init__(
        self,
        raid_name: str,
        requester_id: int,
        raids: list[dict],
        waiting_members: list[dict],
        excluded_members: list[dict],
        moving_member: dict,
        source_text: str,
        target_raid_no: int,
        target_party_no: int,
    ):
        super().__init__(timeout=120)
        self.raid_name = raid_name
        self.requester_id = requester_id
        self.raids = raids
        self.waiting_members = waiting_members
        self.excluded_members = excluded_members
        self.moving_member = moving_member
        self.source_text = source_text
        self.target_raid_no = target_raid_no
        self.target_party_no = target_party_no

        self.selected_target_name = None
        self.selected_destination = None

        target_party = self.raids[target_raid_no - 1][f"party{target_party_no}"]

        target_options = [
            SelectOption(
                label=f"{m['name']} ({m['job']})",
                value=m["name"],
                description=f"{m['user_name']} | {m['ilvl']} | {m['score']}"
            )
            for m in target_party[:25]
        ]

        self.target_select = discord.ui.Select(
            placeholder="밀어낼 공대원을 선택하세요",
            min_values=1,
            max_values=1,
            options=target_options
        )
        self.target_select.callback = self.target_select_callback
        self.add_item(self.target_select)

        destination_options = [
            SelectOption(label="대기", value="waiting", description="선택한 공대원을 대기 인원으로 이동"),
            SelectOption(label="제외", value="excluded", description="선택한 공대원을 제외 인원으로 이동"),
        ]

        for idx, raid in enumerate(self.raids, start=1):
            for party_no in (1, 2):
                if idx == self.target_raid_no and party_no == self.target_party_no:
                    continue

                party = raid[f"party{party_no}"]
                if len(party) < 4:
                    destination_options.append(
                        SelectOption(
                            label=f"{idx}공대 {party_no}파티",
                            value=f"raid:{idx}:{party_no}",
                            description=f"현재 {len(party)}명"
                        )
                    )

        self.destination_select = discord.ui.Select(
            placeholder="밀어낸 공대원을 어디로 이동할지 선택하세요",
            min_values=1,
            max_values=1,
            options=destination_options[:25]
        )
        self.destination_select.callback = self.destination_select_callback
        self.add_item(self.destination_select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "이 수정 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True
            )
            return False
        return True

    async def target_select_callback(self, interaction: discord.Interaction):
        self.selected_target_name = self.target_select.values[0]
        await interaction.response.defer()

    async def destination_select_callback(self, interaction: discord.Interaction):
        self.selected_destination = self.destination_select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="확정", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_target_name:
            await interaction.response.send_message("먼저 밀어낼 공대원을 선택해주세요.", ephemeral=True)
            return

        if not self.selected_destination:
            await interaction.response.send_message("밀어낸 공대원의 이동 위치를 선택해주세요.", ephemeral=True)
            return

        try:
            found_target = find_member_in_saved_parties(
                self.raids,
                self.waiting_members,
                self.excluded_members,
                self.selected_target_name
            )
            if not found_target:
                await interaction.response.send_message("선택한 공대원을 찾을 수 없습니다.", ephemeral=True)
                return

            displaced_member = remove_member_from_saved_parties(
                self.raids,
                self.waiting_members,
                self.excluded_members,
                found_target
            )

            target_party = self.raids[self.target_raid_no - 1][f"party{self.target_party_no}"]
            target_party.append(self.moving_member)

            if self.selected_destination == "waiting":
                self.waiting_members.append(displaced_member)
                displaced_text = "대기"

            elif self.selected_destination == "excluded":
                self.excluded_members.append(displaced_member)
                displaced_text = "제외"

            else:
                _, raid_no_str, party_no_str = self.selected_destination.split(":")
                raid_no = int(raid_no_str)
                party_no = int(party_no_str)
                self.raids[raid_no - 1][f"party{party_no}"].append(displaced_member)
                displaced_text = f"{raid_no}공대 {party_no}파티"

            save_generated_parties(
                self.raid_name,
                self.raids,
                self.waiting_members,
                self.excluded_members
            )

            embed = make_simple_embed(
                title="✅ 공대 수정 완료",
                description=(
                    f"레이드: **{self.raid_name}**\n"
                    f"이동 캐릭터: **{self.moving_member['name']}**\n"
                    f"이동 전: **{self.source_text}**\n"
                    f"이동 후: **{self.target_raid_no}공대 {self.target_party_no}파티**\n\n"
                    f"밀려난 캐릭터: **{displaced_member['name']}**\n"
                    f"이동 위치: **{displaced_text}**"
                )
            )
            await interaction.response.edit_message(embed=embed, view=None)

        except Exception:
            logging.exception("가득 찬 파티 교체 저장 실패")
            embed = make_simple_embed(
                title="❌ 공대 수정 실패",
                description="가득 찬 파티 교체 처리 중 오류가 발생했습니다."
            )
            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = make_simple_embed(title="✅ 공대 수정이 취소되었습니다.")
        await interaction.response.edit_message(embed=embed, view=None)
