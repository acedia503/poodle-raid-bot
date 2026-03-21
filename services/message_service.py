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

    def build_application_embed(self, application: RaidApplication) -> discord.Embed:
        embed = discord.Embed(title="레이드 신청 완료")
        embed.add_field(name="캐릭터명", value=application.character_name, inline=False)
        embed.add_field(name="직업", value=application.job, inline=False)
        embed.add_field(name="아이템레벨", value=str(application.item_level), inline=False)
        embed.add_field(name="전투력", value=f"{application.combat_power:,}", inline=False)
        embed.add_field(name="레이드", value=application.raid_name, inline=False)
        return embed

    def build_application_list_embed(self, applications: list[RaidApplication]) -> discord.Embed:
        embed = discord.Embed(title="신청 내역")
        if not applications:
            embed.description = "신청 내역이 없습니다."
            return embed

        for app in applications[:10]:
            embed.add_field(
                name=f"{app.character_name} / {app.raid_name}",
                value=f"{app.job} | IL {app.item_level} | CP {app.combat_power:,}",
                inline=False,
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

    def build_application_result_text(
        self,
        raid_name: str,
        info: dict,
        result_type: str,
        show_identity: bool,
    ):
        if result_type == "updated":
            title = f"{raid_name} 신청 정보가 갱신되었습니다."
        else:
            title = f"{raid_name} 신청이 완료되었습니다."
    
        lines = [
            f"**캐릭터명** : {info['character_name']}",
            f"**직업** : {info['job']}",
        ]
    
        if show_identity:
            lines.append(f"**종족** : {info['race']}")
            lines.append(f"**서버** : {info['server']}")
    
        lines.extend([
            f"**아이템레벨** : {info['item_level']}",
            f"**전투력** : {info['combat_power']:,}",
        ])
    
        return title + "\n\n" + "\n".join(lines)
    
    def build_application_all_result_text(self, info: dict, applications: list, show_identity: bool) -> str:
        lines = [
            "전체 레이드 신청 내역",
            "",
            f"**캐릭터명** : {info['character_name']}",
            f"**직업** : {info['job']}",
        ]
    
        if show_identity:
            lines.append(f"**종족** : {info['race']}")
            lines.append(f"**서버** : {info['server']}")
    
        lines.extend([
            f"**아이템레벨** : {info['item_level']}",
            f"**전투력** : {info['combat_power']:,}",
            "",
            "**신청 레이드**",
        ])
    
        for app in applications:
            lines.append(f"- {app.raid_name}")
    
        return "\n".join(lines)
