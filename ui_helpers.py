# ui_helpers.py
# embed / 텍스트 포맷 / 공대 결과 출력 유틸

from __future__ import annotations

from typing import Any

import discord


EMBED_FIELD_LIMIT = 1024
EMBED_TITLE_LIMIT = 256
EMBED_DESCRIPTION_LIMIT = 4096
SAFE_TEXT_LIMIT = 1000
TABLE_LINE_LIMIT = 80


def make_simple_embed(title: str, description: str | None = None) -> discord.Embed:
    safe_title = safe_str(title, "안내")[:EMBED_TITLE_LIMIT]
    safe_description = None
    if description is not None:
        safe_description = safe_str(description, "-")[:EMBED_DESCRIPTION_LIMIT]
    return discord.Embed(title=safe_title, description=safe_description)


def safe_str(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def split_text_by_lines(text: str, limit: int = SAFE_TEXT_LIMIT) -> list[str]:
    if not text:
        return ["-"]

    lines = str(text).split("\n")
    chunks: list[str] = []
    current = ""

    for raw_line in lines:
        line = raw_line.rstrip()
        appended = f"{current}\n{line}" if current else line

        if len(appended) <= limit:
            current = appended
            continue

        if current:
            chunks.append(current)
            current = ""

        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]

        current = line

    if current:
        chunks.append(current)

    return chunks or ["-"]


def split_lines_by_length(lines: list[str], limit: int = 3800) -> list[str]:
    chunks: list[str] = []
    current = ""

    for line in lines:
        line = str(line)

        if not current:
            current = line
            continue

        if len(current) + 1 + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += "\n" + line

    if current:
        chunks.append(current)

    return chunks


def add_long_text_fields(
    embed: discord.Embed,
    field_name: str,
    text: str,
    inline: bool = False,
) -> None:
    chunks = split_text_by_lines(text, limit=SAFE_TEXT_LIMIT)

    for idx, chunk in enumerate(chunks, start=1):
        name = field_name if idx == 1 else f"{field_name} ({idx})"
        embed.add_field(
            name=safe_str(name, "내용")[:EMBED_TITLE_LIMIT],
            value=safe_str(chunk, "-")[:EMBED_FIELD_LIMIT],
            inline=inline,
        )


def _fit_text(value: Any, width: int) -> str:
    text = safe_str(value)
    if len(text) > width:
        return text[: max(1, width - 1)] + "…"
    return text.ljust(width)


def _fit_number(value: Any, width: int) -> str:
    text = str(safe_int(value))
    if len(text) > width:
        return text[-width:]
    return text.rjust(width)


def format_member_line(
    user_name: str,
    char_name: str,
    job: str,
    ilvl: int,
    score: int,
    status: str,
) -> str:
    return (
        f"`{safe_str(user_name)}` | "
        f"`{safe_str(char_name)}` | "
        f"`{safe_str(job)}` | "
        f"템렙 `{safe_int(ilvl)}` | "
        f"아툴 `{safe_int(score)}` | "
        f"**{safe_str(status)}**"
    )


def format_member_simple(member: dict[str, Any]) -> str:
    user_name = _fit_text(member.get("user_name", "알수없음"), 10)
    char_name = _fit_text(member.get("name"), 10)
    job = _fit_text(member.get("job"), 8)
    ilvl = _fit_number(member.get("ilvl"), 4)
    score = _fit_number(member.get("score"), 5)

    line = f"{user_name} | {char_name} | {job} | {ilvl} | {score}"
    return line[:TABLE_LINE_LIMIT]


def _party_table_lines(members: list[dict[str, Any]]) -> list[str]:
    header = "유저명       | 캐릭명       | 직업       | 템렙 |  아툴"
    separator = "-" * len(header)

    if not members:
        return [header, separator, "-"]

    return [header, separator] + [format_member_simple(m) for m in members]


def format_party_block(members: list[dict[str, Any]]) -> str:
    lines = _party_table_lines(members)

    full_block = "```" + "\n".join(lines) + "```"
    if len(full_block) <= EMBED_FIELD_LIMIT:
        return full_block

    trimmed_lines: list[str] = []
    for line in lines:
        candidate_lines = trimmed_lines + [line]
        candidate_block = "```" + "\n".join(candidate_lines) + "\n...```"
        if len(candidate_block) > EMBED_FIELD_LIMIT:
            break
        trimmed_lines.append(line)

    if not trimmed_lines:
        shortened = lines[0][: EMBED_FIELD_LIMIT - 10]
        return f"```{shortened}\n...```"

    return "```" + "\n".join(trimmed_lines) + "\n...```"


def calc_party_stats(members: list[dict[str, Any]]) -> tuple[int, int, int]:
    total_members = len(members)
    total_ilvl = sum(safe_int(m.get("ilvl"), 0) for m in members)
    total_score = sum(safe_int(m.get("score"), 0) for m in members)
    return total_members, total_ilvl, total_score


def build_party_result_embeds(
    레이드이름: str,
    raids: list[dict[str, Any]],
    waiting_members: list[dict[str, Any]],
    excluded_members: list[dict[str, Any]] | None = None,
) -> list[discord.Embed]:
    if excluded_members is None:
        excluded_members = []

    embeds: list[discord.Embed] = []
    safe_raid_name = safe_str(레이드이름, "레이드")

    for idx, raid in enumerate(raids, start=1):
        party1 = raid.get("party1", [])
        party2 = raid.get("party2", [])
        total_members = party1 + party2

        member_count, total_ilvl, total_score = calc_party_stats(total_members)
        avg_ilvl = round(total_ilvl / member_count) if member_count else 0
        avg_score = round(total_score / member_count) if member_count else 0

        embed = make_simple_embed(
            title=f"⚔️ {safe_raid_name} {idx}공대",
            description=(
                f"인원: **{member_count}명** | "
                f"평균 템렙: **{avg_ilvl}** | "
                f"평균 아툴: **{avg_score}**"
            ),
        )

        embed.add_field(
            name=f"1파티 ({len(party1)}명)",
            value=format_party_block(party1),
            inline=False,
        )
        embed.add_field(
            name=f"2파티 ({len(party2)}명)",
            value=format_party_block(party2),
            inline=False,
        )
        embeds.append(embed)

    if waiting_members:
        waiting_lines = [format_member_simple(m) for m in waiting_members]
        waiting_embed = make_simple_embed(title=f"⏳ 대기 인원 ({len(waiting_members)}명)")
        add_long_text_fields(
            waiting_embed,
            "목록",
            "\n".join(waiting_lines),
            inline=False,
        )
        embeds.append(waiting_embed)

    if excluded_members:
        excluded_lines = [format_member_simple(m) for m in excluded_members]
        excluded_embed = make_simple_embed(title=f"🚫 제외 인원 ({len(excluded_members)}명)")
        add_long_text_fields(
            excluded_embed,
            "목록",
            "\n".join(excluded_lines),
            inline=False,
        )
        embeds.append(excluded_embed)

    if not embeds:
        embeds.append(
            make_simple_embed(
                title=f"⚠️ {safe_raid_name}",
                description="표시할 공대 결과가 없습니다.",
            )
        )

    return embeds
