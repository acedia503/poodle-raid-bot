# bot.py
# 디스코드 명령어만 담당

import os
import logging
import discord
from discord.ext import commands
from discord import app_commands

from models import Character
from atool import get_character_info
from raid_logic import build_balanced_raids, format_raid_result
from storage import save_active_raids, load_active_raids, init_db

from dotenv import load_dotenv
load_dotenv()

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


# =========================
# 유틸 함수
# =========================

def split_message_by_lines(text: str, limit: int = 1900):
    """디스코드 메시지 길이 제한 때문에 줄 단위로 안전하게 분할"""
    lines = text.split("\n")
    chunks = []
    current = ""

    for line in lines:
        # 현재 chunk에 line 추가 시 limit 초과하면 새 chunk 생성
        appended = f"{current}\n{line}" if current else line
        if len(appended) > limit:
            if current:
                chunks.append(current)
            # line 자체가 limit보다 긴 경우 강제 분할
            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
            current = line
        else:
            current = appended

    if current:
        chunks.append(current)

    return chunks


def safe_character_data(name: str):
    """아툴 조회 후 기본값 포함해 안전하게 반환"""
    data = get_character_info(name)
    return {
        "ilvl": data.get("ilvl", 0),
        "job": data.get("job", "알수없음"),
        "score": data.get("score", 0),
    }


# =========================
# 봇 이벤트
# =========================

@bot.event
async def on_ready():
    try:
        init_db()
        synced = await bot.tree.sync()
        print(f"{bot.user} 레이드봇 준비 완료 / 슬래시 명령어 {len(synced)}개 동기화")
    except Exception:
        logging.exception("슬래시 커맨드 동기화 실패")
        print(f"{bot.user} 로그인 완료, 하지만 슬래시 커맨드 동기화 실패")


# =========================
# /레이드목록추가 레이드이름 입장템렙
# =========================

@bot.tree.command(name="레이드목록추가", description="레이드 목록 추가")
@app_commands.describe(
    레이드이름="레이드 이름",
    입장템렙="입장 가능한 최소 템렙"
)
@app_commands.checks.has_permissions(administrator=True)
async def create_raid(interaction: discord.Interaction, 레이드이름: str, 입장템렙: int):
    if 레이드이름 in active_raids:
        await interaction.response.send_message("이미 존재하는 레이드입니다.", ephemeral=True)
        return

    active_raids[레이드이름] = {
        "min_ilvl": 입장템렙,
        "members": []
    }

    save_active_raids(active_raids)

    await interaction.response.send_message(
        f"✅ {레이드이름} 레이드가 목록에 추가되었습니다.\n"
        f"📌 입장 조건: 템렙 {입장템렙} 이상"
    )


# =========================
# /레이드목록
# =========================

@bot.tree.command(name="레이드목록", description="현재 등록된 레이드 목록 조회")
async def raid_list(interaction: discord.Interaction):
    if not active_raids:
        await interaction.response.send_message("등록된 레이드가 없습니다.")
        return

    lines = ["[레이드 목록]"]

    for raid_name, raid_data in active_raids.items():
        min_ilvl = raid_data["min_ilvl"]
        member_count = len(raid_data["members"])
        lines.append(f"{raid_name} | 입장조건: {min_ilvl} | 신청자 수: {member_count}")

    msg = "\n".join(lines)
    await interaction.response.send_message(msg)


# =========================
# /레이드목록삭제 레이드이름
# =========================

@bot.tree.command(name="레이드목록삭제", description="레이드 목록 삭제")
@app_commands.describe(
    레이드이름="삭제할 레이드 이름"
)
@app_commands.checks.has_permissions(administrator=True)
async def delete_raid(interaction: discord.Interaction, 레이드이름: str):
    if 레이드이름 not in active_raids:
        await interaction.response.send_message(
            "존재하지 않는 레이드입니다.",
            ephemeral=True
        )
        return

    member_count = len(active_raids[레이드이름]["members"])

    del active_raids[레이드이름]
    save_active_raids(active_raids)

    await interaction.response.send_message(
        f"⚠️ 레이드 삭제 완료\n"
        f"레이드: {레이드이름}\n"
        f"신청자 {member_count}명이 함께 삭제되었습니다."
    )


# =========================
# /신청 레이드이름 캐릭터명
# =========================

@bot.tree.command(name="신청", description="레이드 신청")
@app_commands.describe(
    레이드이름="신청할 레이드 이름",
    캐릭터명="아툴에서 조회할 캐릭터명"
)
async def apply_raid(
    interaction: discord.Interaction,
    레이드이름: str,
    캐릭터명: str
):
    if 레이드이름 not in active_raids:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    members = active_raids[레이드이름]["members"]

    # 같은 유저가 같은 캐릭터로 중복 신청 방지
    for member in members:
        if member.user_id == interaction.user.id and member.name == 캐릭터명:
            await interaction.response.send_message(
                "이미 신청한 캐릭터입니다.",
                ephemeral=True
            )
            return

    try:
        data = safe_character_data(캐릭터명)
    except Exception:
        logging.exception("아툴 조회 실패")
        await interaction.response.send_message(
            "아툴 조회에 실패했습니다. 잠시 후 다시 시도해주세요.",
            ephemeral=True
        )
        return

    min_ilvl = active_raids[레이드이름]["min_ilvl"]

    if data["ilvl"] < min_ilvl:
        await interaction.response.send_message(
            f"❌ 신청 불가\n"
            f"레이드: {레이드이름}\n"
            f"필요 템렙: {min_ilvl}\n"
            f"현재 템렙: {data['ilvl']}",
            ephemeral=True
        )
        return

    char = Character(
        user_id=interaction.user.id,
        user_name=interaction.user.display_name,
        name=캐릭터명
    )

    members.append(char)
    save_active_raids(active_raids)

    await interaction.response.send_message(
        f"✅ 신청 완료\n"
        f"레이드: {레이드이름}\n"
        f"캐릭터: {캐릭터명}\n"
        f"직업: {data['job']}\n"
        f"템렙: {data['ilvl']}\n"
        f"아툴 점수: {data['score']}"
    )


# =========================
# /신청취소 레이드이름 캐릭터명
# =========================

@bot.tree.command(name="신청취소", description="레이드 신청 취소")
@app_commands.describe(
    레이드이름="신청 취소할 레이드 이름",
    캐릭터명="취소할 캐릭터명"
)
async def cancel_apply(
    interaction: discord.Interaction,
    레이드이름: str,
    캐릭터명: str
):
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

    await interaction.response.send_message(
        f"✅ 신청 취소 완료\n레이드: {레이드이름}\n캐릭터: {removed_member.name}"
    )


# =========================
# /신청목록 레이드이름
# =========================

@bot.tree.command(name="신청목록", description="레이드 신청 목록")
@app_commands.describe(레이드이름="조회할 레이드 이름")
async def list_members(interaction: discord.Interaction, 레이드이름: str):
    if 레이드이름 not in active_raids:
        await interaction.response.send_message("존재하지 않는 레이드입니다.", ephemeral=True)
        return

    await interaction.response.defer()

    members = active_raids[레이드이름]["members"]
    if not members:
        await interaction.followup.send("신청자가 없습니다.")
        return

    min_ilvl = active_raids[레이드이름]["min_ilvl"]
    lines = [f"[{레이드이름}] 신청 목록 (최신 아툴 기준)"]

    for m in members:
        try:
            data = safe_character_data(m.name)
            status = "신청가능" if data["ilvl"] >= min_ilvl else "입장불가"

            lines.append(
                f"{m.user_name} | {m.name} | 직업: {data['job']} | "
                f"아이템레벨: {data['ilvl']} | 아툴점수: {data['score']} | 상태: {status}"
            )

        except Exception as e:
            logging.exception("신청목록 아툴 조회 실패")
            lines.append(
                f"{m.user_name} | {m.name} | 아툴조회실패: {type(e).__name__}: {e}"
            )

    msg = "\n".join(lines)

    chunks = split_message_by_lines(msg)
    for chunk in chunks:
        await interaction.followup.send(chunk)


# =========================
# /신청삭제 레이드이름 캐릭터명
# =========================

@bot.tree.command(name="신청삭제", description="운영자가 특정 신청을 강제로 삭제")
@app_commands.describe(
    레이드이름="신청을 삭제할 레이드 이름",
    캐릭터명="삭제할 캐릭터명"
)
@app_commands.checks.has_permissions(administrator=True)
async def force_cancel_apply(
    interaction: discord.Interaction,
    레이드이름: str,
    캐릭터명: str
):
    if 레이드이름 not in active_raids:
        await interaction.response.send_message(
            "존재하지 않는 레이드입니다.",
            ephemeral=True
        )
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

    await interaction.response.send_message(
        f"🗑️ 강제 신청 삭제 완료\n"
        f"레이드: {레이드이름}\n"
        f"캐릭터: {target_member.name}\n"
        f"신청자: {target_member.user_name}"
    )


# =========================
# /공대생성 레이드이름
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
            ilvl = data["ilvl"]
            job = data["job"]
            score = data["score"]

            if ilvl < min_ilvl:
                invalid_members.append(
                    f"{m.user_name} | {m.name} | {ilvl} | 입장불가"
                )
                continue

            refreshed_members.append({
                "user_id": m.user_id,
                "user_name": m.user_name,
                "name": m.name,
                "job": job,
                "ilvl": ilvl,
                "score": score
            })

        except Exception as e:
            logging.exception("공대생성 아툴 조회 실패")
            invalid_members.append(
                f"{m.user_name} | {m.name} | 아툴조회실패: {type(e).__name__}: {e}"
            )

    if len(refreshed_members) < 8:
        msg = "공대를 만들 수 있는 인원이 부족합니다.\n"
        msg += f"현재 유효 인원: {len(refreshed_members)}명\n"
        if invalid_members:
            msg += "\n[제외 인원]\n" + "\n".join(invalid_members)

        for chunk in split_message_by_lines(msg):
            await interaction.followup.send(chunk)
        return

    raids, waiting_members, error = build_balanced_raids(refreshed_members)

    if error:
        msg = error
        if invalid_members:
            msg += "\n\n[제외 인원]\n" + "\n".join(invalid_members)

        for chunk in split_message_by_lines(msg):
            await interaction.followup.send(chunk)
        return

    msg = format_raid_result(레이드이름, raids, waiting_members, invalid_members)

    for chunk in split_message_by_lines(msg):
        await interaction.followup.send(chunk)


# =========================
# 관리자 권한 없을 때 에러 메시지
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
# 기타 미처리 app command 에러
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
