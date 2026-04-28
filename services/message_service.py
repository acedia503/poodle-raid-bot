import discord

from domain.channel_raid import ChannelRaid
from domain.guild_setting import GuildSetting
from domain.raid_application import RaidApplication


class MessageService:
    def build_guild_setting_embed(self, setting: GuildSetting | None) -> discord.Embed:
        embed = discord.Embed(title="기본 설정")

        if setting is None:
            embed.description = "저장된 기본 설정이 없습니다."
            return embed

        embed.description = (
            f"**종족** : {setting.default_race or '-'}\n"
            f"**서버** : {setting.default_server or '-'}"
        )
        return embed

    def build_channel_raid_embed(self, channel_raid: ChannelRaid | None) -> discord.Embed:
        embed = discord.Embed(title="레이드 설정")

        if channel_raid is None:
            embed.description = "현재 채널에 연결된 레이드가 없습니다."
            return embed

        embed.description = (
            f"**레이드명** : {channel_raid.raid_name}\n"
            f"**입장조건** : {channel_raid.min_item_level if channel_raid.min_item_level is not None else '-'}"
        )
        return embed

    def build_character_info_embed(self, info: dict) -> discord.Embed:
        text = (
            f"**캐릭터명** : {info.get('character_name')}\n"
            f"**직업** : {info.get('job')}\n"
            f"**종족** : {info.get('race')}\n"
            f"**서버** : {info.get('server')}\n"
            f"**아이템레벨** : {info.get('item_level')}\n"
            f"**전투력** : {int(info.get('combat_power') or 0):,}"
        )

        embed = discord.Embed(
            title="캐릭터 정보",
            description=text,
        )
        return embed

    def build_application_result_embed(
        self,
        raid_name: str,
        info: dict,
        result_type: str,
        show_identity: bool,
    ) -> discord.Embed:
        if result_type == "created":
            title = f"✅ {raid_name} 신청 완료"
    
            lines = [
                f"**캐릭터명** : {info['character_name']}",
            ]
    
            if show_identity:
                lines.append(f"**종족** : {info['race']}")
                lines.append(f"**서버** : {info['server']}")
    
            lines.extend([
                f"**직업** : {info['job']}",
                f"**아이템레벨** : {info['item_level']}",
                f"**전투력** : {info['combat_power']:,}",
            ])
    
            return discord.Embed(
                description=title + "\n\n" + "\n".join(lines),
                color=discord.Color.green(),
            )
    
        if result_type == "rejected":
            title = f"⛔ {raid_name} 신청 불가"
    
            lines = [
                f"**캐릭터명** : {info['character_name']}",
            ]
    
            if show_identity:
                lines.append(f"**종족** : {info['race']}")
                lines.append(f"**서버** : {info['server']}")
    
            lines.extend([
                f"**직업** : {info['job']}",
                f"**아이템레벨** : {info['item_level']}",
                f"**전투력** : {info['combat_power']:,}",
                "",
                "**사유** : 입장 조건인 아이템 레벨이 충족하지 않습니다.",
            ])
    
            min_item_level = info.get("min_item_level")
            if min_item_level is not None:
                lines.append(f"**입장조건** : [아이템레벨] {min_item_level}")
    
            return discord.Embed(
                description=title + "\n\n" + "\n".join(lines),
                color=discord.Color.red(),
            )
    
        if result_type == "already_exists_other_user":
            title = f"⚠️ {raid_name} 신청 중복"
    
            lines = [
                f"**디코유저** : {info.get('user_name', '-')}",
                f"**캐릭터명** : {info['character_name']}",
            ]
    
            if show_identity:
                lines.append(f"**종족** : {info['race']}")
                lines.append(f"**서버** : {info['server']}")
    
            lines.extend([
                f"**직업** : {info['job']}",
                f"**아이템레벨** : {info['item_level']}",
                f"**전투력** : {info['combat_power']:,}",
                "",
                "**사유** : 해당 캐릭터는 다른 유저의 캐릭터로 등록되어 있습니다. 관리자에게 문의해주세요.",
            ])
    
            return discord.Embed(
                description=title + "\n\n" + "\n".join(lines),
                color=discord.Color.orange(),
            )
    
        if result_type in ("show_current", "updated"):
            title = f"🔄 {raid_name} 신청 정보가 업데이트되었습니다."
        elif result_type == "cancelled":
            title = f"❌ {raid_name} 신청 취소 완료"
        else:
            title = f"{raid_name} 신청 정보"
    
        lines = [
            f"**캐릭터명** : {info['character_name']}",
        ]
    
        if show_identity:
            lines.append(f"**종족** : {info['race']}")
            lines.append(f"**서버** : {info['server']}")
    
        lines.extend([
            f"**직업** : {info['job']}",
            f"**아이템레벨** : {info['item_level']}",
            f"**전투력** : {info['combat_power']:,}",
        ])
    
        return discord.Embed(
            description=title + "\n\n" + "\n".join(lines),
            color=discord.Color.blurple(),
        )

    def build_application_all_embed(
        self,
        info: dict,
        applications: list[RaidApplication],
        show_identity: bool,
    ) -> discord.Embed:
        lines = [
            f"**캐릭터명** : {info['character_name']}",
        ]

        if show_identity:
            lines.append(f"**종족** : {info['race']}")
            lines.append(f"**서버** : {info['server']}")

        lines.extend([
            f"**직업** : {info['job']}",
            f"**아이템레벨** : {info['item_level']}",
            f"**전투력** : {info['combat_power']:,}",
            "",
            "신청 레이드",
        ])

        added = set()
        for app in applications:
            if app.raid_name not in added:
                lines.append(f"- {app.raid_name}")
                added.add(app.raid_name)

        return discord.Embed(
            title="전체 레이드 신청 내역",
            description="\n".join(lines),
        )

    def build_admin_application_list_embed(
        self,
        raid_name: str,
        applications: list[RaidApplication],
        show_identity: bool,
    ) -> discord.Embed:
        total_count = len(applications)

        embed = discord.Embed(
            title=f"{raid_name} 신청내역 (총 {total_count}명)"
        )

        if not applications:
            embed.description = "신청자가 없습니다."
            return embed

        lines = []
        for idx, app in enumerate(applications, start=1):
            if show_identity:
                lines.append(
                    f"{idx}. {app.user_name} | {app.character_name} | {app.race} | {app.server} | "
                    f"{app.job} | {app.item_level} | {app.combat_power:,}"
                )
            else:
                lines.append(
                    f"{idx}. {app.user_name} | {app.character_name} | "
                    f"{app.job} | {app.item_level} | {app.combat_power:,}"
                )

        embed.description = "\n".join(lines)
        return embed

    def build_admin_delete_search_embed(
        self,
        title: str,
        applications: list[RaidApplication],
        show_identity: bool,
    ) -> discord.Embed:
        embed = discord.Embed(title=title)

        if not applications:
            embed.description = "검색 결과가 없습니다."
            return embed

        lines = []
        for idx, app in enumerate(applications, start=1):
            if show_identity:
                lines.append(
                    f"{idx}. {app.user_name} | {app.character_name} | {app.race} | {app.server} | "
                    f"{app.job} | {app.item_level} | {app.combat_power:,}"
                )
            else:
                lines.append(
                    f"{idx}. {app.user_name} | {app.character_name} | "
                    f"{app.job} | {app.item_level} | {app.combat_power:,}"
                )

        embed.description = "\n".join(lines)
        return embed

    def build_admin_user_search_result_embed(
        self,
        title: str,
        users: list[dict],
    ) -> discord.Embed:
        embed = discord.Embed(title=title)

        if not users:
            embed.description = "검색 결과가 없습니다."
            return embed

        lines = []
        for idx, user in enumerate(users, start=1):
            lines.append(f"{idx}. {user['user_name']}")

        embed.description = "\n".join(lines)
        return embed
