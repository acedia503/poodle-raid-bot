from domain.raid_rule import RaidRule
from repositories.raid_rule_repository import RaidRuleRepository

class PartyRuleService:
    JOB_NONE = "없음"

    def __init__(self, raid_rule_repository: RaidRuleRepository):
        self.raid_rule_repository = raid_rule_repository

    def get_rule(self, guild_id: int, channel_id: int, raid_name: str) -> RaidRule | None:
        return self.raid_rule_repository.find_by_channel_and_raid(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name,
        )

    def create_default_rule(self, guild_id: int, channel_id: int, raid_name: str) -> RaidRule:
        rule = RaidRule.empty(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name,
        )
        self.raid_rule_repository.save(rule)
        return rule

    def get_or_create_rule(self, guild_id: int, channel_id: int, raid_name: str) -> RaidRule:
        rule = self.get_rule(guild_id, channel_id, raid_name)
        if rule is not None:
            return rule
        return self.create_default_rule(guild_id, channel_id, raid_name)

    def reset_rule(self, guild_id: int, channel_id: int, raid_name: str) -> RaidRule:
        rule = RaidRule.empty(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name,
        )
        self.raid_rule_repository.upsert(rule)
        return rule

    def update_rule(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
        party1_priority_jobs: list[str],
        party1_preferred_jobs: list[str],
        party2_priority_jobs: list[str],
        party2_preferred_jobs: list[str],
    ) -> RaidRule:
        rule = RaidRule(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name,
            party1_priority_jobs=self._normalize_jobs(party1_priority_jobs),
            party1_preferred_jobs=self._normalize_jobs(party1_preferred_jobs),
            party2_priority_jobs=self._normalize_jobs(party2_priority_jobs),
            party2_preferred_jobs=self._normalize_jobs(party2_preferred_jobs),
        )
        self.raid_rule_repository.upsert(rule)
        return rule

    def _normalize_jobs(self, jobs: list[str] | None) -> list[str]:
        if not jobs:
            return []

        cleaned = []
        for job in jobs:
            if not job:
                continue
            if job == self.JOB_NONE:
                return []
            if job not in cleaned:
                cleaned.append(job)

        return cleaned
