import discord
from discord.ui import View, Button, Select

from constants.jobs import JOB_OPTIONS


def jobs_to_text(jobs: list[str]) -> str:
    return ", ".join(jobs) if jobs else "없음"


def build_rule_detail_embed(rule) -> discord.Embed:
    embed = discord.Embed(
        title="공대 생성 규칙",
        description=(
            "각 파티에 우선 배치할 직업과 선호 직업을 확인할 수 있습니다."
        ),
    )
    embed.add_field(
        name="1파티",
        value=(
            f"우선 직업: {jobs_to_text(rule.party1_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(rule.party1_preferred_jobs)}"
        ),
        inline=False,
    )
    embed.add_field(
        name="2파티",
        value=(
            f"우선 직업: {jobs_to_text(rule.party2_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(rule.party2_preferred_jobs)}"
        ),
        inline=False,
    )
    return embed


def build_rule_edit_embed(
    party1_priority_jobs: list[str],
    party1_preferred_jobs: list[str],
    party2_priority_jobs: list[str],
    party2_preferred_jobs: list[str],
) -> discord.Embed:
    embed = discord.Embed(
        title="공대 생성 규칙 수정",
        description=(
            "각 파티에 우선 배치할 직업과 선호 직업을 설정해주세요.\n"
            "선호 직업은 필요한 경우에만 선택하면 됩니다."
        ),
    )
    embed.add_field(
        name="1파티",
        value=(
            f"우선 직업: {jobs_to_text(party1_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(party1_preferred_jobs)}"
        ),
        inline=False,
    )
    embed.add_field(
        name="2파티",
        value=(
            f"우선 직업: {jobs_to_text(party2_priority_jobs)}\n"
            f"선호 직업: {jobs_to_text(party2_preferred_jobs)}"
        ),
        inline=False,
    )
    return embed
