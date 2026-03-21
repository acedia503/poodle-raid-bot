from domain.channel_raid import ChannelRaid
from domain.guild_setting import GuildSetting
from domain.party_build_session import PartyBuildSession
from domain.party_slot import PartySlot
from domain.party_waiting_member import PartyWaitingMember
from domain.raid_application import RaidApplication
from utils.constants import SAFE_MESSAGE_LIMIT
from utils.formatters import format_number


class MessageService:
    def build_application_embed(self, application: RaidApplication):
        # TODO: discord.Embed로 구현
        return {
            "title": "신청 완료",
            "fields": [
                ("캐릭터명", application.character_name),
                ("직업", application.job),
                ("아이템레벨", str(application.item_level)),
                ("전투력", format_number(application.combat_power)),
                ("레이드", application.raid_name),
            ],
        }

    def build_application_list_embed(self, applications: list[RaidApplication]):
        # TODO: discord.Embed로 구현
        return {
            "title": "신청 목록",
            "count": len(applications),
        }

    def build_channel_raid_embed(self, channel_raid: ChannelRaid | None):
        if channel_raid is None:
            return {"title": "현재 채널 레이드", "description": "연결된 레이드가 없습니다."}
        return {
            "title": "현재 채널 레이드",
            "fields": [
                ("레이드명", channel_raid.raid_name),
                ("최소 아이템레벨", str(channel_raid.min_item_level or "-")),
                ("최소 전투력", str(channel_raid.min_combat_power or "-")),
                ("기타 조건", channel_raid.entry_condition_text or "-"),
            ],
        }

    def build_guild_setting_embed(self, setting: GuildSetting | None):
        if setting is None:
            return {"title": "서버 기본 설정", "description": "기본 설정이 없습니다."}
        return {
            "title": "서버 기본 설정",
            "fields": [
                ("기본 종족", setting.default_race or "-"),
                ("기본 서버", setting.default_server or "-"),
            ],
        }

    def build_party_result_text(
        self,
        session: PartyBuildSession,
        slots: list[PartySlot],
        waiting: list[PartyWaitingMember],
        applications_map: dict[int, RaidApplication] | None = None,
    ) -> str:
        lines: list[str] = [f"[{session.raid_name} 공대 편성]"]

        grouped: dict[int, dict[int, list[PartySlot]]] = {}
        for slot in slots:
            grouped.setdefault(slot.group_no, {}).setdefault(slot.party_no, []).append(slot)

        for group_no in sorted(grouped.keys()):
            lines.append("")
            lines.append(f"{group_no}공대")
            for party_no in sorted(grouped[group_no].keys()):
                lines.append(f"{party_no}파티")
                party_slots = sorted(grouped[group_no][party_no], key=lambda x: x.slot_no)
                for slot in party_slots:
                    lines.append(
                        f"{slot.slot_no}번 {slot.character_name} / {slot.job} / {format_number(slot.combat_power or 0)}"
                    )

        if waiting:
            lines.append("")
            lines.append("[대기/제외]")
            for member in waiting:
                if applications_map and member.application_id in applications_map:
                    app = applications_map[member.application_id]
                    lines.append(f"- {app.character_name} / {app.job} / {member.waiting_status.value}")
                else:
                    lines.append(f"- application_id={member.application_id} / {member.waiting_status.value}")

        return "\n".join(lines)

    def split_message(self, text: str, limit: int = SAFE_MESSAGE_LIMIT) -> list[str]:
        if len(text) <= limit:
            return [text]

        chunks: list[str] = []
        current = []

        for line in text.splitlines():
            candidate = "\n".join(current + [line])
            if len(candidate) > limit and current:
                chunks.append("\n".join(current))
                current = [line]
            else:
                current.append(line)

        if current:
            chunks.append("\n".join(current))

        return chunks

    def build_error_message(self, message: str) -> str:
        return f"❌ {message}"
