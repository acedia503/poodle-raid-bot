# bot.py
# 디스코드 명령어 담당

from __future__ import annotations

import logging
import os
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from atool import get_character_info
from models import Character
from raid_logic import (
    build_balanced_raids,
    format_raid_result,
    format_saved_raid_result,
)
from storage import (
    add_raid_member,
    init_db,
    load_active_raids,
    load_generated_parties,
    remove_raid_member,
    save_generated_parties,
    save_raid,
    save_raid_members,
)
from party_helpers import (
    find_member_in_saved_parties,
    remove_member_from_saved_parties,
    place_member_to_destination,
    get_party_size,
)
from ui_helpers import (
    make_simple_embed,
    add_long_text_fields,
    build_party_result_embeds,
    split_lines_by_length,
)
from views import (
    ClearPartyView,
    DeleteRaidConfirmView,
    FullPartyResolveView,
)

# =========================
# 기본 설정
# =========================

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("환경변수 DISCORD_TOKEN 이 설정되지 않았습니다.")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# DB 초기화 후 로드
init_db()
active_raids = load_active_raids()

# 비워두면 모든 서버 허용
ALLOWED_GUILD_IDS: set[int] = set()
# 예시:
# ALLOWED_GUILD_IDS = {
#     123456789012345678,
#     987654321098765432,
# }


# =========================
# 공통 유틸
# =========================

def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def refresh_active_raids() -> None:
    global active_raids
    active_raids = load_active_raids()


def is_allowed_guild(interaction: discord.Interaction) -> bool:
    if not ALLOWED_GUILD_IDS:
        return True
    return interaction.guild is not None and interaction.guild.id in ALLOWED_GUILD_IDS


def get_raid_data(raid_name: str) -> dict[str, Any] | None:
    return active_raids.get(raid_name)


def safe_character_data(name: str) -> dict[str, Any]:
    data = get_character_info(name) or {}
    return {
        "ilvl": safe_int(data.get("ilvl"), 0),
        "job": str(data.get("job", "알수없음") or "알수없음").strip() or "알수없음",
        "score": safe_int(data.get("score"), 0),
        "max_score": safe_int(data.get("max_score"), 0),
    }


def build_found_location_text(found: dict[str, Any]) -> str:
    location = found.get("location")

    if location == "raid":
        raid_index = safe_int(found.get("raid_index"), 0)
        party_name = found.get("party_name", "party1")
        party_no = 1 if party_name == "party1" else 2
        return f"{raid_index + 1}공대 {party_no}파티"

    if location == "waiting":
        return "대기"

    if location == "excluded":
        return "제외"

    return "알수없음"


def raid_has_same_user_in_saved_raids(
    raids: list[dict[str, list[dict[str, Any]]]],
    target_raid_index: int,
    user_id: int,
    ignore_name: str | None = None,
) -> bool:
    if target_raid_index < 0 or target_raid_index >= len(raids):
        return False

    target_raid = raids[target_raid_index]
    ignore_name = (ignore_name or "").strip()

    for party_name in ("party1", "party2"):
        for member in target_raid.get(party_name, []):
            member_user_id = safe_int(member.get("user_id"), 0)
            member_name = str(member.get("name", "")).strip()

            if member_user_id != user_id:
                continue

            if ignore_name and member_name == ignore_name:
                continue

            return True

    return False


async def send_interaction_message(
    interaction: discord.Interaction,
    content: str | None = None,
    *,
    embed: discord.Embed | None = None,
    view: discord.ui.View | None = None,
    ephemeral: bool = False,
) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(
            content=content,
            embed=embed,
            view=view,
            ephemeral=ephemeral,
        )
    else:
        await interaction.response.send_message(
            content=content,
            embed=embed,
            view=view,
            ephemeral=ephemeral,
        )


async def send_long_text_followup(
    interaction: discord.Interaction,
    text: str,
    limit: int = 1800,
    ephemeral: bool = False,
):
    lines = str(text).split("\n")

    chunks = split_lines_by_length(lines, limit=limit)

    for chunk in chunks:
        await interaction.followup.send(
            f"```{chunk}```",
            ephemeral=ephemeral,
        )


# =========================
# 이벤트
# =========================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        logging.info("동기화 완료: %d개", len(synced))
    except Exception:
        logging.exception("명령어 동기화 실패")

    logging.info("%s 로그인 완료", bot.user)


# =========================
# /레이드생성
# =========================

@bot.tree.command(name="레이드생성", description="레이드 목록 추가")
@app_commands.describe(
    레이드이름="레이드 이름",
    입장템렙="입장 가능한 최소 템렙",
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def create_raid(interaction: discord.Interaction, 레이드이름: str, 입장템렙: int):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    레이드이름 = 레이드이름.strip()

    if not 레이드이름:
        await interaction.response.send_message("레이드 이름이 비어 있습니다.", ephemeral=True)
        return

    if 레이드이름 in active_raids:
        await interaction.response.send_message("이미 존재하는 레이드입니다.", ephemeral=True)
        return

    if 입장템렙 < 0:
        await interaction.response.send_message("입장 템렙은 0 이상이어야 합니다.", ephemeral=True)
        return

    try:
        save_raid(레이드이름, 입장템렙)
        save_raid_members(레이드이름, [])
        refresh_active_raids()
    except Exception:
        logging.exception("레이드 생성 저장 실패")
        await interaction.response.send_message(
            "레이드 생성 저장 중 오류가 발생했습니다.",
            ephemeral=True,
        )
        return

    embed = make_simple_embed(
        title="✅ 레이드 추가 완료",
        description=f"레이드: **{레이드이름}**\n입장 조건: **템렙 {입장템렙} 이상**",
    )
    await interaction.response.send_message(embed=embed)


# =========================
# /레이드확인
# =========================

@bot.tree.command(name="레이드확인", description="현재 등록된 레이드 목록 조회")
async def raid_list(interaction: discord.Interaction):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    try:
        refresh_active_raids()
        latest_raids = active_raids
    except Exception:
        logging.exception("레이드 목록 조회 실패")
        await interaction.response.send_message(
            "레이드 목록을 불러오는 중 오류가 발생했습니다.",
            ephemeral=True,
        )
        return

    if not latest_raids:
        await interaction.response.send_message("등록된 레이드가 없습니다.")
        return

    embed = make_simple_embed(title="📋 레이드 목록")

    lines: list[str] = []
    for raid_name, raid_data in latest_raids.items():
        min_ilvl = safe_int(raid_data.get("min_ilvl"), 0)
        members = raid_data.get("members", [])
        member_count = len(members) if isinstance(members, list) else 0
        lines.append(
            f"**{raid_name}** | 입장조건 `템렙 {min_ilvl}` | 신청자 `{member_count}명`"
        )

    add_long_text_fields(embed, "목록", "\n".join(lines))
    embed.set_footer(text=f"총 레이드 수: {len(latest_raids)}개")

    await interaction.response.send_message(embed=embed)


# =========================
# /레이드삭제
# =========================

@bot.tree.command(name="레이드삭제", description="레이드 목록 삭제")
@app_commands.describe(레이드이름="삭제할 레이드 이름")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def delete_raid_command(interaction: discord.Interaction, 레이드이름: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    raid_data = get_raid_data(레이드이름)
    if raid_data is None:
        await interaction.response.send_message(
            "존재하지 않는 레이드입니다.",
            ephemeral=True,
        )
        return

    member_count = len(raid_data.get("members", []))

    embed = make_simple_embed(
        title="⚠️ 레이드 삭제 확인",
        description=(
            f"레이드: **{레이드이름}**\n"
            f"현재 신청자 수: **{member_count}명**\n\n"
            f"삭제하면 **신청목록도 함께 삭제됩니다.**\n"
            f"계속하려면 아래 버튼을 눌러주세요."
        ),
    )

    view = DeleteRaidConfirmView(
        raid_name=레이드이름,
        requester_id=interaction.user.id,
        active_raids=active_raids,
    )

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True,
    )


# =========================
# /신청
# =========================

@bot.tree.command(name="신청", description="레이드 신청")
@app_commands.describe(
    레이드이름="신청할 레이드 이름",
    캐릭터명="아툴에서 조회할 캐릭터명",
)
async def apply_raid(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=False)

    레이드이름 = 레이드이름.strip()
    캐릭터명 = 캐릭터명.strip()

    raid_data = get_raid_data(레이드이름)
    if raid_data is None:
        await interaction.followup.send("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    if not 캐릭터명:
        await interaction.followup.send("캐릭터명이 비어 있습니다.", ephemeral=True)
        return

    members = raid_data.get("members", [])
    for member in members:
        member_name = getattr(member, "name", None)
        if member_name == 캐릭터명:
            await interaction.followup.send("이미 신청한 캐릭터입니다.", ephemeral=True)
            return

    try:
        data = safe_character_data(캐릭터명)
    except Exception:
        logging.exception("아툴 조회 실패")
        await interaction.followup.send(
            "아툴 조회에 실패했습니다. 잠시 후 다시 시도해주세요.",
            ephemeral=True,
        )
        return

    min_ilvl = safe_int(raid_data.get("min_ilvl"), 0)
    if data["ilvl"] < min_ilvl:
        embed = make_simple_embed(
            title="❌ 신청 불가",
            description=(
                f"레이드: **{레이드이름}**\n"
                f"필요 템렙: **{min_ilvl}**\n"
                f"현재 템렙: **{data['ilvl']}**"
            ),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    char = Character(
        user_id=interaction.user.id,
        user_name=interaction.user.display_name,
        name=캐릭터명,
    )

    try:
        inserted = add_raid_member(레이드이름, char)
        if not inserted:
            await interaction.followup.send("이미 신청한 캐릭터입니다.", ephemeral=True)
            return
        refresh_active_raids()
    except Exception:
        logging.exception("DB 신청 저장 실패")
        await interaction.followup.send(
            "신청 저장 중 오류가 발생했습니다.",
            ephemeral=True,
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
        ),
    )
    await interaction.followup.send(embed=embed, ephemeral=False)


# =========================
# /신청취소
# =========================

@bot.tree.command(name="신청취소", description="레이드 신청 취소")
@app_commands.describe(
    레이드이름="신청 취소할 레이드 이름",
    캐릭터명="취소할 캐릭터명",
)
async def cancel_apply(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    레이드이름 = 레이드이름.strip()
    캐릭터명 = 캐릭터명.strip()

    raid_data = get_raid_data(레이드이름)
    if raid_data is None:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    members = raid_data.get("members", [])

    target_member = None
    for member in members:
        if getattr(member, "user_id", None) == interaction.user.id and getattr(member, "name", None) == 캐릭터명:
            target_member = member
            break

    if target_member is None:
        await interaction.response.send_message(
            f"취소할 신청 내역이 없습니다.\n레이드: {레이드이름}\n캐릭터: {캐릭터명}",
            ephemeral=True,
        )
        return

    try:
        removed = remove_raid_member(레이드이름, interaction.user.id, 캐릭터명)
        if not removed:
            await interaction.response.send_message(
                "취소할 신청 내역이 없습니다.",
                ephemeral=True,
            )
            return
        refresh_active_raids()
    except Exception:
        logging.exception("신청취소 DB 저장 실패")
        await interaction.response.send_message(
            "신청 취소 저장 중 오류가 발생했습니다.",
            ephemeral=True,
        )
        return

    embed = make_simple_embed(
        title="✅ 신청 취소 완료",
        description=f"레이드: **{레이드이름}**\n캐릭터: **{캐릭터명}**",
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================
# /신청목록
# =========================

@bot.tree.command(name="신청목록", description="레이드 신청 목록")
@app_commands.describe(레이드이름="조회할 레이드 이름")
async def list_members(interaction: discord.Interaction, 레이드이름: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    raid_data = get_raid_data(레이드이름)
    if raid_data is None:
        await interaction.response.send_message(
            "존재하지 않는 레이드입니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    members = raid_data.get("members", [])
    if not members:
        await interaction.followup.send("신청자가 없습니다.", ephemeral=True)
        return

    min_ilvl = safe_int(raid_data.get("min_ilvl"), 0)

    success_lines: list[str] = []
    fail_lines: list[str] = []

    for idx, member in enumerate(members, start=1):
        try:
            char_name = getattr(member, "name", "")
            user_name = getattr(member, "user_name", "알수없음")
            data = safe_character_data(char_name)
            status = "신청가능" if data["ilvl"] >= min_ilvl else "입장불가"

            success_lines.append(
                f"{idx}. {user_name} | {char_name} | {data['job']} | "
                f"템렙 {data['ilvl']} | 아툴 {data['score']} | {status}"
            )
        except Exception as e:
            logging.exception("신청목록 아툴 조회 실패")
            fail_lines.append(
                f"{idx}. {getattr(member, 'user_name', '알수없음')} | "
                f"{getattr(member, 'name', '-')} | 조회실패: {type(e).__name__}"
            )

    all_lines: list[str] = [
        f"입장 조건: **템렙 {min_ilvl} 이상**",
        "",
        "**신청자 목록**",
    ]
    all_lines.extend(success_lines)

    if fail_lines:
        all_lines.extend(["", "**조회 실패**"])
        all_lines.extend(fail_lines)

    chunks = split_lines_by_length(all_lines, limit=1900)

    for page, chunk in enumerate(chunks, start=1):
        title = f"📋 {레이드이름} 신청 목록"
        if len(chunks) > 1:
            title += f" ({page}/{len(chunks)})"

        embed = make_simple_embed(title=title, description=chunk)

        if page == len(chunks):
            embed.set_footer(text=f"총 신청자 수: {len(members)}명")

        await interaction.followup.send(embed=embed, ephemeral=True)


# =========================
# /신청삭제
# =========================

@bot.tree.command(name="신청삭제", description="운영자가 특정 신청을 강제로 삭제")
@app_commands.describe(
    레이드이름="신청을 삭제할 레이드 이름",
    캐릭터명="삭제할 캐릭터명",
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def force_cancel_apply(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    레이드이름 = 레이드이름.strip()
    캐릭터명 = 캐릭터명.strip()

    raid_data = get_raid_data(레이드이름)
    if raid_data is None:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    members = raid_data.get("members", [])
    target_member = None

    for member in members:
        if getattr(member, "name", None) == 캐릭터명:
            target_member = member
            break

    if target_member is None:
        await interaction.response.send_message(
            f"삭제할 신청 내역이 없습니다.\n레이드: {레이드이름}\n캐릭터: {캐릭터명}",
            ephemeral=True,
        )
        return

    try:
        removed = remove_raid_member(
            레이드이름,
            getattr(target_member, "user_id", 0),
            getattr(target_member, "name", 캐릭터명),
        )
        if not removed:
            await interaction.response.send_message(
                "삭제할 신청 내역이 없습니다.",
                ephemeral=True,
            )
            return
        refresh_active_raids()
    except Exception:
        logging.exception("강제 신청삭제 DB 저장 실패")
        await interaction.response.send_message(
            "강제 신청 삭제 저장 중 오류가 발생했습니다.",
            ephemeral=True,
        )
        return

    embed = make_simple_embed(
        title="🗑️ 강제 신청 삭제 완료",
        description=(
            f"레이드: **{레이드이름}**\n"
            f"캐릭터: **{getattr(target_member, 'name', 캐릭터명)}**\n"
            f"신청자: **{getattr(target_member, 'user_name', '알수없음')}**"
        ),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================
# /공대생성
# =========================

@bot.tree.command(name="공대생성", description="레이드 공대 자동 생성")
@app_commands.describe(레이드이름="공대를 생성할 레이드 이름")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def raid_create(interaction: discord.Interaction, 레이드이름: str):
    await make_party(interaction, 레이드이름)


async def make_party(interaction: discord.Interaction, 레이드이름: str):
    if not is_allowed_guild(interaction):
        await send_interaction_message(
            interaction,
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    raid_data = get_raid_data(레이드이름)
    if raid_data is None:
        await send_interaction_message(
            interaction,
            "존재하지 않는 레이드입니다.",
            ephemeral=True,
        )
        return

    members = raid_data.get("members", [])
    if not members:
        await send_interaction_message(
            interaction,
            "신청자가 없습니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    min_ilvl = safe_int(raid_data.get("min_ilvl"), 0)

    refreshed_members: list[dict[str, Any]] = []
    invalid_members: list[str] = []

    for member in members:
        try:
            char_name = str(getattr(member, "name", "")).strip()
            user_name = str(getattr(member, "user_name", "알수없음")).strip()

            if not char_name:
                invalid_members.append(f"{user_name} | 캐릭터명없음 | 조회실패")
                continue

            data = safe_character_data(char_name)

            if safe_int(data.get("ilvl"), 0) < min_ilvl:
                invalid_members.append(
                    f"{user_name} | {char_name} | {safe_int(data.get('ilvl'), 0)} | 입장불가"
                )
                continue

            refreshed_members.append({
                "user_id": safe_int(getattr(member, "user_id", 0), 0),
                "user_name": user_name or "알수없음",
                "name": char_name,
                "job": str(data.get("job", "-")).strip() or "-",
                "ilvl": safe_int(data.get("ilvl"), 0),
                "score": safe_int(data.get("score"), 0),
            })

        except Exception:
            logging.exception("공대생성 아툴 조회 실패")
            invalid_members.append(
                f"{getattr(member, 'user_name', '알수없음')} | "
                f"{getattr(member, 'name', '-')} | 조회실패"
            )

    if len(refreshed_members) < 8:
        fail_lines = [
            "❌ 공대 생성 실패",
            f"유효 인원이 부족합니다. 현재 인원: {len(refreshed_members)}명",
        ]

        if invalid_members:
            fail_lines.append("")
            fail_lines.append("[제외 인원]")
            fail_lines.extend(invalid_members)

        await send_long_text_followup(interaction, "\n".join(fail_lines))
        return

    raids, waiting_members, build_invalid_members = build_balanced_raids(refreshed_members)
    all_invalid_members = invalid_members + build_invalid_members

    if not raids:
        fail_lines = [
            "❌ 공대 생성 실패",
            "공대를 생성할 수 없습니다.",
        ]

        if all_invalid_members:
            fail_lines.append("")
            fail_lines.append("[제외 인원]")
            fail_lines.extend(all_invalid_members)

        await send_long_text_followup(interaction, "\n".join(fail_lines))
        return

    result_text = format_raid_result(
        레이드이름,
        raids,
        waiting_members,
        all_invalid_members,
    )

    try:
        save_generated_parties(레이드이름, raids, waiting_members, [])
    except Exception:
        logging.exception("공대 저장 실패")
        result_text += (
            "\n\n[저장 상태]\n"
            "공대 생성 결과는 표시했지만 저장 중 오류가 발생했습니다."
        )
        await send_long_text_followup(interaction, result_text)
        return

    await send_long_text_followup(interaction, result_text)

# =========================
# /공대확인
# =========================

@bot.tree.command(name="공대확인", description="저장된 공대 편성 조회")
@app_commands.describe(레이드이름="조회할 레이드 이름")
async def party_list(interaction: discord.Interaction, 레이드이름: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    if 레이드이름 not in active_raids:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    is_admin = interaction.user.guild_permissions.administrator
    is_ephemeral = not is_admin

    await interaction.response.defer(ephemeral=is_ephemeral)

    try:
        raids, waiting_members, excluded_members = load_generated_parties(레이드이름)
    except Exception:
        logging.exception("공대목록 조회 실패")
        await interaction.followup.send(
            "저장된 공대 정보를 불러오는 중 오류가 발생했습니다.",
            ephemeral=is_ephemeral,
        )
        return

    if not raids and not waiting_members and not excluded_members:
        await interaction.followup.send(
            f"[{레이드이름}] 저장된 공대가 없습니다.\n먼저 /공대생성을 실행해주세요.",
            ephemeral=is_ephemeral,
        )
        return

    result_text = format_saved_raid_result(
        레이드이름,
        raids,
        waiting_members,
        excluded_members,
    )
    await send_long_text_followup(
        interaction,
        result_text,
        ephemeral=is_ephemeral,
    )


# =========================
# /공대초기화
# =========================

@bot.tree.command(name="공대초기화", description="저장된 공대 편성만 초기화")
@app_commands.describe(레이드이름="초기화할 레이드 이름")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def clear_party(interaction: discord.Interaction, 레이드이름: str):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    if 레이드이름 not in active_raids:
        await interaction.response.send_message(
            "존재하지 않는 레이드입니다.",
            ephemeral=True,
        )
        return

    try:
        raids, waiting_members, excluded_members = load_generated_parties(레이드이름)
    except Exception:
        logging.exception("공대초기화 사전 조회 실패")
        await interaction.response.send_message(
            "저장된 공대 정보를 확인하는 중 오류가 발생했습니다.",
            ephemeral=True,
        )
        return

    total_party_members = sum(len(r["party1"]) + len(r["party2"]) for r in raids)
    total_waiting = len(waiting_members)
    total_excluded = len(excluded_members)

    if total_party_members == 0 and total_waiting == 0 and total_excluded == 0:
        embed = make_simple_embed(
            title="📭 초기화할 공대 없음",
            description=f"레이드: **{레이드이름}**\n저장된 공대 편성이 없습니다.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = make_simple_embed(
        title="⚠️ 공대 초기화 확인",
        description=(
            f"레이드: **{레이드이름}**\n"
            f"현재 공대원 수: **{total_party_members}명**\n"
            f"현재 대기 인원 수: **{total_waiting}명**\n"
            f"현재 제외 인원 수: **{total_excluded}명**\n\n"
            f"초기화하면 **저장된 공대 편성만 삭제**됩니다.\n"
            f"**신청목록은 유지됩니다.**"
        ),
    )

    view = ClearPartyView(
        raid_name=레이드이름,
        requester_id=interaction.user.id,
    )

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True,
    )


# =========================
# /공대수정
# =========================

@bot.tree.command(name="공대수정", description="저장된 공대에서 캐릭터를 공대/대기/제외로 이동")
@app_commands.describe(
    레이드이름="수정할 레이드 이름",
    캐릭터명="이동할 캐릭터명",
    이동종류="공대 / 대기 / 제외",
    대상공대="이동종류가 공대일 때 대상 공대 번호",
    대상파티="이동종류가 공대일 때 대상 파티 번호(1 또는 2)",
)
@app_commands.choices(
    이동종류=[
        app_commands.Choice(name="공대", value="raid"),
        app_commands.Choice(name="대기", value="waiting"),
        app_commands.Choice(name="제외", value="excluded"),
    ],
    대상파티=[
        app_commands.Choice(name="1파티", value=1),
        app_commands.Choice(name="2파티", value=2),
    ],
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def modify_party(
    interaction: discord.Interaction,
    레이드이름: str,
    캐릭터명: str,
    이동종류: app_commands.Choice[str],
    대상공대: int | None = None,
    대상파티: app_commands.Choice[int] | None = None,
):
    if not is_allowed_guild(interaction):
        await interaction.response.send_message(
            "이 서버에서는 사용할 수 없는 봇입니다.",
            ephemeral=True,
        )
        return

    레이드이름 = 레이드이름.strip()
    캐릭터명 = 캐릭터명.strip()

    if 레이드이름 not in active_raids:
        await interaction.response.send_message(
            "존재하지 않는 레이드입니다.",
            ephemeral=True,
        )
        return

    try:
        raids, waiting_members, excluded_members = load_generated_parties(레이드이름)
    except Exception:
        logging.exception("공대수정 공대 불러오기 실패")
        await interaction.response.send_message(
            "저장된 공대 정보를 불러오는 중 오류가 발생했습니다.",
            ephemeral=True,
        )
        return

    if not raids and not waiting_members and not excluded_members:
        await interaction.response.send_message(
            "저장된 공대 정보가 없습니다. 먼저 `/공대생성`을 실행해주세요.",
            ephemeral=True,
        )
        return

    target_member = None

    for raid in raids:
        for party_name in ("party1", "party2"):
            for member in raid.get(party_name, []):
                if str(member.get("name", "")).strip() == 캐릭터명:
                    target_member = member
                    break
            if target_member:
                break
        if target_member:
            break

    if target_member is None:
        for member in waiting_members:
            if str(member.get("name", "")).strip() == 캐릭터명:
                target_member = member
                break

    if target_member is None:
        for member in excluded_members:
            if str(member.get("name", "")).strip() == 캐릭터명:
                target_member = member
                break

    if target_member is None:
        await interaction.response.send_message(
            "저장된 공대/대기/제외 목록에서 해당 캐릭터를 찾을 수 없습니다.",
            ephemeral=True,
        )
        return

    found = find_member_in_saved_parties(
        raids,
        waiting_members,
        excluded_members,
        캐릭터명,
    )

    if not found:
        await interaction.response.send_message(
            "해당 캐릭터의 현재 위치를 찾을 수 없습니다.",
            ephemeral=True,
        )
        return

    source_text = build_found_location_text(found)
    move_type = 이동종류.value

    if move_type == "waiting" and found["location"] == "waiting":
        await interaction.response.send_message(
            f"이미 대기 상태입니다.\n현재 위치: {source_text}",
            ephemeral=True,
        )
        return

    if move_type == "excluded" and found["location"] == "excluded":
        await interaction.response.send_message(
            f"이미 제외 상태입니다.\n현재 위치: {source_text}",
            ephemeral=True,
        )
        return

    if move_type == "raid":
        if 대상공대 is None or 대상파티 is None:
            await interaction.response.send_message(
                "공대 이동에는 대상공대와 대상파티를 함께 입력해야 합니다.",
                ephemeral=True,
            )
            return

        if 대상공대 < 1 or 대상공대 > len(raids):
            await interaction.response.send_message(
                f"대상공대는 1 ~ {len(raids)} 범위여야 합니다.",
                ephemeral=True,
            )
            return

        target_party_no = 대상파티.value
        target_party_name = f"party{target_party_no}"
        target_raid_index = 대상공대 - 1
        target_party = raids[target_raid_index][target_party_name]

        if (
            found["location"] == "raid"
            and found.get("raid_index") == target_raid_index
            and found.get("party_name") == target_party_name
        ):
            await interaction.response.send_message(
                f"이미 {대상공대}공대 {target_party_no}파티에 있습니다.",
                ephemeral=True,
            )
            return

        moving_user_id = safe_int(target_member.get("user_id"), 0)
        moving_name = str(target_member.get("name", "")).strip()

        if raid_has_same_user_in_saved_raids(
            raids,
            target_raid_index=target_raid_index,
            user_id=moving_user_id,
            ignore_name=moving_name,
        ):
            await interaction.response.send_message(
                "같은 공대 안에는 동일한 신청자(user_id)의 캐릭터를 둘 이상 배치할 수 없습니다.",
                ephemeral=True,
            )
            return

        if get_party_size(target_party) >= 4:
            view = FullPartyResolveView(
                raid_name=레이드이름,
                requester_id=interaction.user.id,
                raids=raids,
                waiting_members=waiting_members,
                excluded_members=excluded_members,
                moving_member=target_member,
                source_text=source_text,
                target_raid_no=대상공대,
                target_party_no=target_party_no,
                source_location_type=found["location"],
                source_raid_index=found.get("raid_index"),
                source_party_name=found.get("party_name"),
            )

            embed = make_simple_embed(
                title="⚠️ 대상 파티가 가득 참",
                description=(
                    f"레이드: **{레이드이름}**\n"
                    f"이동 캐릭터: **{moving_name}**\n"
                    f"현재 위치: **{source_text}**\n"
                    f"대상 위치: **{대상공대}공대 {target_party_no}파티**\n\n"
                    f"추가 이동할 공대원과 그 공대원의 이동 위치를 선택해주세요."
                ),
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        removed_member = remove_member_from_saved_parties(
            raids,
            waiting_members,
            excluded_members,
            found,
        )
        if not removed_member:
            await interaction.response.send_message(
                "현재 위치에서 캐릭터를 제거하지 못했습니다.",
                ephemeral=True,
            )
            return

        try:
            place_member_to_destination(
                raids,
                waiting_members,
                excluded_members,
                removed_member,
                move_type="raid",
                target_raid_no=대상공대,
                target_party_no=target_party_no,
            )
            save_generated_parties(레이드이름, raids, waiting_members, excluded_members)
        except Exception:
            logging.exception("공대수정 저장 실패(공대 이동)")
            await interaction.response.send_message(
                "공대 이동 저장 중 오류가 발생했습니다.",
                ephemeral=True,
            )
            return

        embed = make_simple_embed(
            title="✅ 공대 수정 완료",
            description=(
                f"레이드: **{레이드이름}**\n"
                f"캐릭터: **{removed_member['name']}**\n"
                f"이동 전: **{source_text}**\n"
                f"이동 후: **{대상공대}공대 {target_party_no}파티**"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    removed_member = remove_member_from_saved_parties(
        raids,
        waiting_members,
        excluded_members,
        found,
    )
    if not removed_member:
        await interaction.response.send_message(
            "현재 위치에서 캐릭터를 제거하지 못했습니다.",
            ephemeral=True,
        )
        return

    try:
        place_member_to_destination(
            raids,
            waiting_members,
            excluded_members,
            removed_member,
            move_type=move_type,
        )
        save_generated_parties(레이드이름, raids, waiting_members, excluded_members)
    except Exception:
        logging.exception("공대수정 저장 실패(%s)", move_type)
        await interaction.response.send_message(
            "공대 수정 저장 중 오류가 발생했습니다.",
            ephemeral=True,
        )
        return

    move_text = "대기" if move_type == "waiting" else "제외"

    embed = make_simple_embed(
        title="✅ 공대 수정 완료",
        description=(
            f"레이드: **{레이드이름}**\n"
            f"캐릭터: **{removed_member['name']}**\n"
            f"이동 전: **{source_text}**\n"
            f"이동 후: **{move_text}**"
        ),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================
# /아툴
# =========================

@bot.tree.command(name="아툴", description="개인 아툴 점수 조회")
@app_commands.describe(캐릭터명="조회할 캐릭터 이름")
async def search_atool(interaction: discord.Interaction, 캐릭터명: str):
    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        data = safe_character_data(캐릭터명)

        embed = make_simple_embed(
            title="아툴 조회 결과",
            description=f"캐릭터명: **{캐릭터명}**",
        )
        embed.add_field(name="직업", value=str(data.get("job", "알수없음")), inline=False)
        embed.add_field(name="아이템 레벨", value=str(data.get("ilvl", 0)), inline=False)
        embed.add_field(name="아툴 전투 점수", value=str(data.get("score", 0)), inline=False)
        embed.add_field(name="달성 최고 점수", value=str(data.get("max_score", 0)), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logging.exception("개인 아툴 조회 실패")
        await interaction.followup.send(
            f"조회 실패: {type(e).__name__}: {e}",
            ephemeral=True,
        )


# =========================
# 관리자 권한 에러
# =========================

@create_raid.error
@delete_raid_command.error
@force_cancel_apply.error
@raid_create.error
@clear_party.error
@modify_party.error
async def admin_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        if interaction.response.is_done():
            await interaction.followup.send(
                "이 명령어는 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "이 명령어는 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
        return

    logging.exception("관리자 명령어 처리 중 예외 발생")
    if interaction.response.is_done():
        await interaction.followup.send(
            f"명령어 처리 중 오류가 발생했습니다: {type(error).__name__}",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            f"명령어 처리 중 오류가 발생했습니다: {type(error).__name__}",
            ephemeral=True,
        )


# =========================
# 기타 app command 에러
# =========================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logging.exception("슬래시 명령어 예외 발생")

    if interaction.response.is_done():
        await interaction.followup.send(
            f"오류가 발생했습니다: {type(error).__name__}",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            f"오류가 발생했습니다: {type(error).__name__}",
            ephemeral=True,
        )


bot.run(TOKEN)


