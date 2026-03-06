# bot.py
# 디스코드 명령어 담당

import os
import logging
import discord
from discord.ext import commands
from discord import app_commands

from models import Character
from atool import get_character_info
from raid_logic import build_balanced_raids, format_raid_result
from storage import save_active_raids, load_active_raids, init_db

# =========================
# 기본 설정
# =========================

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("환경변수 DISCORD_TOKEN 이 설정되지 않았습니다.")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

active_raids = load_active_raids()

# 필요하면 특정 서버만 허용
# ALLOWED_GUILD_IDS = {123456789012345678, 987654321098765432}
ALLOWED_GUILD_IDS = set()


# =========================
# 유틸
# =========================

def is_allowed_guild(interaction: discord.Interaction) -> bool:
    if not ALLOWED_GUILD_IDS:
        return True
    return interaction.guild is not None and interaction.guild.id in ALLOWED_GUILD_IDS


def split_text_by_lines(text: str, limit: int = 1000) -> list[str]:
    lines = text.split("\n")
    chunks = []
    current = ""

    for line in lines:
        appended = f"{current}\n{line}" if current else line
        if len(appended) > limit:
            if current:
                chunks.append(current)
            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
            current = line
        else:
            current = appended

    if current:
        chunks.append(current)

    return chunks


def safe_character_data(name: str) -> dict:
    data = get_character_info(name)
    return {
        "ilvl": data.get("ilvl", 0),
        "job": data.get("job", "알수없음"),
        "score": data.get("score", 0),
    }


def ensure_allowed_guild_or_reply(interaction: discord.Interaction) -> bool:
    if not is_allowed_guild(interaction):
        return False
    return True


def make_simple_embed(title: str, description: str | None = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description)
    return embed


def add_long_text_fields(embed: discord.Embed, field_name: str, text: str, inline: bool = False):
    chunks = split_text_by_lines(text, limit=1000)
    for idx, chunk in enumerate(chunks, start=1):
        name = field_name if idx == 1 else f"{field_name} ({idx})"
        embed.add_field(name=name, value=chunk, inline=inline)


def format_member_line(user_name: str, char_name: str, job: str, ilvl: int, score: int, status: str) -> str:
    return (
        f"`{user_name}` | `{char_name}` | `{job}` | "
        f"템렙 `{ilvl}` | 아툴 `{score}` | **{status}**"
    )


# =========================
# 이벤트
# =========================

@bot.event
async def on_ready():
    try:
        init_db()
        synced = await bot.tree.sync()
        print(f"{bot.user} 레이드봇 준비 완료 / 슬래시 명령어 {len(synced)}개 동기화")
    except Exception:
        logging.exception("on_ready 처리 실패")


# =========================
# /레이드목록추가
# =========================

@bot.tree.command(name="레이드목록추가", description="레이드 목록 추가")
@app_commands.describe(
    레이드이름="레이드 이름",
    입장템렙="입장 가능한 최소 템렙"
)
@app_commands.checks.has_permissions(administrator=True)
async def create_raid(interaction: discord.Interaction, 레이드이름: str, 입장템렙: int):
    if not ensure_allowed_guild_or_reply(interaction):
        await interaction.response.send_message("이 서버에서는 사용할 수 없는 봇입니다.", ephemeral=True)
        return

    if 레이드이름 in active_raids:
        await interaction.response.send_message("이미 존재하는 레이드입니다.", ephemeral=True)
        return

    active_raids[레이드이름] = {
        "min_ilvl": 입장템렙,
        "members": []
    }
    save_active_raids(active_raids)

    embed = make_simple_embed(
        title="✅ 레이드 추가 완료",
        description=f"레이드: **{레이드이름}**\n입장 조건: **템렙 {입장템렙} 이상**"
    )
    await interaction.response.send_message(embed=embed)


# =========================
# /레이드목록
# =========================

@bot.tree.command(name="레이드목록", description="현재 등록된 레이드 목록 조회")
async def raid_list(interaction: discord.Interaction):
    if not ensure_allowed_guild_or_reply(interaction):
        await interaction.response.send_message("이 서버에서는 사용할 수 없는 봇입니다.", ephemeral=True)
        return

    if not active_raids:
        await interaction.response.send_message("등록된 레이드가 없습니다.")
        return

    embed = make_simple_embed(title="📋 레이드 목록")

    lines = []
    for raid_name, raid_data in active_raids.items():
        min_ilvl = raid_data["min_ilvl"]
        member_count = len(raid_data["members"])
        lines.append(
            f"**{raid_name}** | 입장조건 `템렙 {min_ilvl}` | 신청자 `{member_count}명`"
        )

    add_long_text_fields(embed, "등록된 레이드", "\n".join(lines))
    embed.set_footer(text=f"총 레이드 수: {len(active_raids)}개")

    await interaction.response.send_message(embed=embed)


# =========================
# /레이드목록삭제
# =========================

@bot.tree.command(name="레이드목록삭제", description="레이드 목록 삭제")
@app_commands.describe(레이드이름="삭제할 레이드 이름")
@app_commands.checks.has_permissions(administrator=True)
async def delete_raid(interaction: discord.Interaction, 레이드이름: str):
    if not ensure_allowed_guild_or_reply(interaction):
        await interaction.response.send_message("이 서버에서는 사용할 수 없는 봇입니다.", ephemeral=True)
        return

    if 레이드이름 not in active_raids:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    member_count = len(active_raids[레이드이름]["members"])
    del active_raids[레이드이름]
    save_active_raids(active_raids)

    embed = make_simple_embed(
        title="🗑️ 레이드 삭제 완료",
        description=(
            f"레이드: **{레이드이름}**\n"
            f"삭제된 신청자 수: **{member_count}명**"
        )
    )
    await interaction.response.send_message(embed=embed)


# =========================
# /신청
# =========================

@bot.tree.command(name="신청", description="레이드 신청")
@app_commands.describe(
    레이드이름="신청할 레이드 이름",
    캐릭터명="아툴에서 조회할 캐릭터명"
)
async def apply_raid(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    print("DEBUG /신청 시작", 레이드이름, 캐릭터명)

    if not ensure_allowed_guild_or_reply(interaction):
        await interaction.response.send_message("이 서버에서는 사용할 수 없는 봇입니다.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    캐릭터명 = 캐릭터명.strip()

    if 레이드이름 not in active_raids:
        print("DEBUG 존재하지 않는 레이드", 레이드이름)
        await interaction.followup.send("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    members = active_raids[레이드이름]["members"]
    print("DEBUG 현재 members 수", len(members))

    for member in members:
        if member.name == 캐릭터명:
            print("DEBUG 중복 신청 감지", 캐릭터명)
            await interaction.followup.send(
                "이미 신청한 캐릭터입니다.",
                ephemeral=True
            )
            return

    try:
        data = safe_character_data(캐릭터명)
        print("DEBUG 아툴 조회 결과", data)
    except Exception as e:
        print("DEBUG 아툴 조회 실패", repr(e))
        logging.exception("아툴 조회 실패")
        await interaction.followup.send(
            "아툴 조회에 실패했습니다. 잠시 후 다시 시도해주세요.",
            ephemeral=True
        )
        return

    min_ilvl = active_raids[레이드이름]["min_ilvl"]
    print("DEBUG min_ilvl", min_ilvl)

    if data["ilvl"] < min_ilvl:
        print("DEBUG 신청불가", data["ilvl"], min_ilvl)
        embed = make_simple_embed(
            title="❌ 신청 불가",
            description=(
                f"레이드: **{레이드이름}**\n"
                f"필요 템렙: **{min_ilvl}**\n"
                f"현재 템렙: **{data['ilvl']}**"
            )
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    char = Character(
        user_id=interaction.user.id,
        user_name=interaction.user.display_name,
        name=캐릭터명
    )

    members.append(char)
    print("DEBUG 저장 직전")

    try:
        save_active_raids(active_raids)
        print("DEBUG 저장 완료")
    except Exception as e:
        print("DEBUG DB 저장 실패", repr(e))
        logging.exception("DB 저장 실패")
        await interaction.followup.send(
            "신청 저장 중 오류가 발생했습니다.",
            ephemeral=True
        )
        return

    embed = make_simple_embed(
        title="✅ 신청 완료",
        description=(
            f"레이드: **{레이드이름}**\n"
            f"캐릭터: **{캐릭터명}**\n"
            f"직업: **{data['job']}**\n"
            f"템렙: **{data['ilvl']}**\n"
            f"아툴 점수: **{data['score']}**"
        )
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


# =========================
# /신청취소
# =========================

@bot.tree.command(name="신청취소", description="레이드 신청 취소")
@app_commands.describe(
    레이드이름="신청 취소할 레이드 이름",
    캐릭터명="취소할 캐릭터명"
)
async def cancel_apply(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if not ensure_allowed_guild_or_reply(interaction):
        await interaction.response.send_message("이 서버에서는 사용할 수 없는 봇입니다.", ephemeral=True)
        return

    if 레이드이름 not in active_raids:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    members = active_raids[레이드이름]["members"]

    target_index = None
    for idx, member in enumerate(members):
        if member.user_id == interaction.user.id and member.name == 캐릭터명:
            target_index = idx
            break

    if target_index is None:
        await interaction.response.send_message(
            f"취소할 신청 내역이 없습니다.\n레이드: {레이드이름}\n캐릭터: {캐릭터명}",
            ephemeral=True
        )
        return

    removed_member = members.pop(target_index)
    save_active_raids(active_raids)

    embed = make_simple_embed(
        title="✅ 신청 취소 완료",
        description=(
            f"레이드: **{레이드이름}**\n"
            f"캐릭터: **{removed_member.name}**"
        )
    )
    await interaction.response.send_message(embed=embed)


# =========================
# /신청목록
# =========================

@bot.tree.command(name="신청목록", description="레이드 신청 목록")
@app_commands.describe(레이드이름="조회할 레이드 이름")
async def list_members(interaction: discord.Interaction, 레이드이름: str):
    if not ensure_allowed_guild_or_reply(interaction):
        await interaction.response.send_message("이 서버에서는 사용할 수 없는 봇입니다.", ephemeral=True)
        return

    if 레이드이름 not in active_raids:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    await interaction.response.defer()

    members = active_raids[레이드이름]["members"]
    if not members:
        await interaction.followup.send("신청자가 없습니다.")
        return

    min_ilvl = active_raids[레이드이름]["min_ilvl"]

    success_lines = []
    fail_lines = []

    for m in members:
        try:
            data = safe_character_data(m.name)
            status = "신청가능" if data["ilvl"] >= min_ilvl else "입장불가"

            success_lines.append(
                format_member_line(
                    m.user_name,
                    m.name,
                    data["job"],
                    data["ilvl"],
                    data["score"],
                    status
                )
            )
        except Exception as e:
            logging.exception("신청목록 아툴 조회 실패")
            fail_lines.append(f"`{m.user_name}` | `{m.name}` | 조회실패: `{type(e).__name__}`")

    embed = make_simple_embed(
        title=f"📋 {레이드이름} 신청 목록",
        description=f"입장 조건: **템렙 {min_ilvl} 이상**"
    )

    if success_lines:
        add_long_text_fields(embed, f"신청자 {len(success_lines)}명", "\n".join(success_lines))

    if fail_lines:
        add_long_text_fields(embed, "조회 실패", "\n".join(fail_lines))

    embed.set_footer(text=f"총 신청자 수: {len(members)}명")
    await interaction.followup.send(embed=embed)


# =========================
# /신청삭제
# =========================

@bot.tree.command(name="신청삭제", description="운영자가 특정 신청을 강제로 삭제")
@app_commands.describe(
    레이드이름="신청을 삭제할 레이드 이름",
    캐릭터명="삭제할 캐릭터명"
)
@app_commands.checks.has_permissions(administrator=True)
async def force_cancel_apply(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if not ensure_allowed_guild_or_reply(interaction):
        await interaction.response.send_message("이 서버에서는 사용할 수 없는 봇입니다.", ephemeral=True)
        return

    if 레이드이름 not in active_raids:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    members = active_raids[레이드이름]["members"]

    target_index = None
    target_member = None

    for idx, member in enumerate(members):
        if member.name == 캐릭터명:
            target_index = idx
            target_member = member
            break

    if target_index is None:
        await interaction.response.send_message(
            f"삭제할 신청 내역이 없습니다.\n레이드: {레이드이름}\n캐릭터: {캐릭터명}",
            ephemeral=True
        )
        return

    members.pop(target_index)
    save_active_raids(active_raids)

    embed = make_simple_embed(
        title="🗑️ 강제 신청 삭제 완료",
        description=(
            f"레이드: **{레이드이름}**\n"
            f"캐릭터: **{target_member.name}**\n"
            f"신청자: **{target_member.user_name}**"
        )
    )
    await interaction.response.send_message(embed=embed)


# =========================
# /공대생성
# =========================

@bot.tree.command(name="공대생성", description="레이드 공대 자동 생성")
@app_commands.describe(레이드이름="공대를 생성할 레이드 이름")
async def make_party(interaction: discord.Interaction, 레이드이름: str):

    if 레이드이름 not in active_raids:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    members = active_raids[레이드이름]["members"]

    if not members:
        await interaction.response.send_message("신청자가 없습니다.")
        return

    await interaction.response.defer()

    min_ilvl = active_raids[레이드이름]["min_ilvl"]

    refreshed_members = []
    invalid_members = []

    for m in members:
        try:
            data = safe_character_data(m.name)

            if data["ilvl"] < min_ilvl:
                invalid_members.append(
                    f"{m.user_name} | {m.name} | {data['ilvl']} | 입장불가"
                )
                continue

            refreshed_members.append({
                "user_id": m.user_id,
                "user_name": m.user_name,
                "name": m.name,
                "job": data["job"],
                "ilvl": data["ilvl"],
                "score": data["score"]
            })

        except Exception as e:
            logging.exception("공대생성 아툴 조회 실패")
            invalid_members.append(
                f"{m.user_name} | {m.name} | 조회실패"
            )

    if len(refreshed_members) < 8:

        embed = discord.Embed(
            title="❌ 공대 생성 실패",
            description=f"유효 인원이 부족합니다\n현재 인원: {len(refreshed_members)}명"
        )

        if invalid_members:
            embed.add_field(
                name="제외 인원",
                value="```\n" + "\n".join(invalid_members[:40]) + "\n```",
                inline=False
            )

        await interaction.followup.send(embed=embed)
        return

    raids, waiting_members, error = build_balanced_raids(refreshed_members)

    if error:
        await interaction.followup.send(error)
        return

    # =========================
    # 공대 Embed 출력
    # =========================

    for idx, raid in enumerate(raids, start=1):

        total_members = raid["party1"] + raid["party2"]

        total_ilvl = sum(m["ilvl"] for m in total_members)
        total_score = sum(m["score"] for m in total_members)

        avg_ilvl = total_ilvl // len(total_members)
        avg_score = total_score // len(total_members)

        embed = discord.Embed(
            title=f"⚔️ {레이드이름} {idx}공대",
            description=f"평균 템렙: **{avg_ilvl}** | 평균 아툴: **{avg_score}**"
        )

        # 1파티
        party1_lines = []
        for m in raid["party1"]:
            party1_lines.append(
                f"{m['user_name']} | {m['name']} | {m['job']} | {m['ilvl']} | {m['score']}"
            )

        embed.add_field(
            name="1파티",
            value="```\n" + "\n".join(party1_lines) + "\n```",
            inline=False
        )

        # 2파티
        party2_lines = []
        for m in raid["party2"]:
            party2_lines.append(
                f"{m['user_name']} | {m['name']} | {m['job']} | {m['ilvl']} | {m['score']}"
            )

        embed.add_field(
            name="2파티",
            value="```\n" + "\n".join(party2_lines) + "\n```",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    # =========================
    # 대기 인원
    # =========================

    if waiting_members:

        lines = []

        for m in waiting_members:
            lines.append(
                f"{m['user_name']} | {m['name']} | {m['job']} | {m['ilvl']} | {m['score']}"
            )

        embed = discord.Embed(
            title="⏳ 대기 인원"
        )

        embed.add_field(
            name=f"{len(waiting_members)}명",
            value="```\n" + "\n".join(lines[:40]) + "\n```",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    # =========================
    # 제외 인원
    # =========================

    if invalid_members:

        embed = discord.Embed(
            title="🚫 제외 인원"
        )

        embed.add_field(
            name=f"{len(invalid_members)}명",
            value="```\n" + "\n".join(invalid_members[:40]) + "\n```",
            inline=False
        )

        await interaction.followup.send(embed=embed)


# =========================
# 관리자 권한 에러
# =========================

@create_raid.error
@delete_raid.error
@force_cancel_apply.error
async def admin_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if interaction.response.is_done():
            await interaction.followup.send(
                "이 명령어는 관리자만 사용할 수 있습니다.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "이 명령어는 관리자만 사용할 수 있습니다.",
                ephemeral=True
            )
        return

    logging.exception("관리자 명령어 처리 중 예외 발생")
    if interaction.response.is_done():
        await interaction.followup.send(
            f"명령어 처리 중 오류가 발생했습니다: {type(error).__name__}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"명령어 처리 중 오류가 발생했습니다: {type(error).__name__}",
            ephemeral=True
        )


# =========================
# 기타 app command 에러
# =========================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    logging.exception("슬래시 명령어 예외 발생")

    if interaction.response.is_done():
        await interaction.followup.send(
            f"오류가 발생했습니다: {type(error).__name__}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"오류가 발생했습니다: {type(error).__name__}",
            ephemeral=True
        )


bot.run(TOKEN)


