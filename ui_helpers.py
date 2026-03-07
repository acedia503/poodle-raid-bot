# ui_helpers.py
# embed / 텍스트 포맷 / 공대 결과 출력 유틸

import discord


def make_simple_embed(title: str, description: str | None = None) -> discord.Embed:
    return discord.Embed(title=title, description=description)


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


def format_party_block(members: list[dict]) -> str:
    if not members:
        return "```-```"

    lines = []
    for m in members:
        lines.append(
            f"{m['user_name']} | {m['name']} | {m['job']} | {m['ilvl']} | {m['score']}"
        )

    text = "\n".join(lines)
    if len(text) > 1000:
        text = text[:995] + "\n..."

    return f"```{text}```"


def build_party_result_embeds(
    레이드이름: str,
    raids: list[dict],
    waiting_members: list[dict],
    excluded_members: list[dict] | None = None
):
    if excluded_members is None:
        excluded_members = []

    embeds = []

    for idx, raid in enumerate(raids, start=1):
        total_members = raid["party1"] + raid["party2"]
        total_ilvl = sum(m["ilvl"] for m in total_members)
        total_score = sum(m["score"] for m in total_members)

        avg_ilvl = total_ilvl // len(total_members) if total_members else 0
        avg_score = total_score // len(total_members) if total_members else 0

        embed = make_simple_embed(
            title=f"⚔️ {레이드이름} {idx}공대",
            description=f"평균 템렙: **{avg_ilvl}** | 평균 아툴: **{avg_score}**"
        )
        embed.add_field(
            name="1파티",
            value=format_party_block(raid["party1"]),
            inline=False
        )
        embed.add_field(
            name="2파티",
            value=format_party_block(raid["party2"]),
            inline=False
        )
        embeds.append(embed)

    if waiting_members:
        waiting_lines = [
            f"{m['user_name']} | {m['name']} | {m['job']} | {m['ilvl']} | {m['score']}"
            for m in waiting_members
        ]
        waiting_embed = make_simple_embed(title="⏳ 대기 인원")
        add_long_text_fields(waiting_embed, f"{len(waiting_members)}명", "\n".join(waiting_lines))
        embeds.append(waiting_embed)

    if excluded_members:
        excluded_lines = [
            f"{m['user_name']} | {m['name']} | {m['job']} | {m['ilvl']} | {m['score']}"
            for m in excluded_members
        ]
        excluded_embed = make_simple_embed(title="🚫 제외 인원")
        add_long_text_fields(excluded_embed, f"{len(excluded_members)}명", "\n".join(excluded_lines))
        embeds.append(excluded_embed)

    return embeds
