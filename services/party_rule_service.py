import json

from domain.enums import BalanceMode
from domain.raid_rule import RaidRule
from repositories.raid_rule_repository import RaidRuleRepository
from utils.constants import DEFAULT_GROUP_SIZE, DEFAULT_PARTY_COUNT, DEFAULT_SLOTS_PER_PARTY


class PartyRuleService:
    def __init__(self, raid_rule_repository: RaidRuleRepository):
        self.raid_rule_repository = raid_rule_repository

    def get_rule(self, guild_id: int, raid_name: str) -> RaidRule | None:
        return self.raid_rule_repository.get_by_guild_and_raid(guild_id, raid_name)

    def get_or_create_default_rule(self, guild_id: int, raid_name: str) -> RaidRule:
        rule = self.get_rule(guild_id, raid_name)
        if rule:
            return rule

        default_rule_data = {
            "preferred_jobs_per_group": {},
            "max_same_job_per_group": 99,
            "sort_priority": ["combat_power", "item_level"],
            "allow_under_condition": False,
        }

        return RaidRule(
            id=None,
            guild_id=guild_id,
            raid_name=raid_name,
            group_size=DEFAULT_GROUP_SIZE,
            party_count=DEFAULT_PARTY_COUNT,
            slots_per_party=DEFAULT_SLOTS_PER_PARTY,
            balance_mode=BalanceMode.MIXED,
            rule_data_json=json.dumps(default_rule_data, ensure_ascii=False),
        )

    def save_rule(
        self,
        guild_id: int,
        raid_name: str,
        group_size: int,
        party_count: int,
        slots_per_party: int,
        balance_mode: str,
        rule_data_json: str | None,
    ) -> RaidRule:
        self.validate_rule(group_size, party_count, slots_per_party)

        rule = RaidRule(
            id=None,
            guild_id=guild_id,
            raid_name=raid_name,
            group_size=group_size,
            party_count=party_count,
            slots_per_party=slots_per_party,
            balance_mode=BalanceMode(balance_mode),
            rule_data_json=rule_data_json,
        )
        return self.raid_rule_repository.upsert(rule)

    def delete_rule(self, guild_id: int, raid_name: str) -> bool:
        return self.raid_rule_repository.delete_by_guild_and_raid(guild_id, raid_name)

    def validate_rule(self, group_size: int, party_count: int, slots_per_party: int) -> None:
        if group_size <= 0 or party_count <= 0 or slots_per_party <= 0:
            raise ValueError("공대 규칙 값은 0보다 커야 합니다.")
        if party_count * slots_per_party != group_size:
            raise ValueError("party_count * slots_per_party 는 group_size 와 같아야 합니다.")
