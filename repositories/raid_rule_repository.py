import json
from typing import Optional

from domain.raid_rule import RaidRule


class RaidRuleRepository:
    def __init__(self, db):
        self.db = db

    def find_by_channel_and_raid(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
    ) -> Optional[RaidRule]:
        query = """
        SELECT
            guild_id,
            channel_id,
            raid_name,
            party1_priority_jobs,
            party1_preferred_jobs,
            party2_priority_jobs,
            party2_preferred_jobs
        FROM raid_rules
        WHERE guild_id = ? AND channel_id = ? AND raid_name = ?
        """
        row = self.db.fetchone(query, (guild_id, channel_id, raid_name))
        if not row:
            return None

        return RaidRule(
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            raid_name=row["raid_name"],
            party1_priority_jobs=json.loads(row["party1_priority_jobs"]),
            party1_preferred_jobs=json.loads(row["party1_preferred_jobs"]),
            party2_priority_jobs=json.loads(row["party2_priority_jobs"]),
            party2_preferred_jobs=json.loads(row["party2_preferred_jobs"]),
        )

    def save(self, rule: RaidRule) -> None:
        query = """
        INSERT INTO raid_rules (
            guild_id,
            channel_id,
            raid_name,
            party1_priority_jobs,
            party1_preferred_jobs,
            party2_priority_jobs,
            party2_preferred_jobs
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(
            query,
            (
                rule.guild_id,
                rule.channel_id,
                rule.raid_name,
                json.dumps(rule.party1_priority_jobs, ensure_ascii=False),
                json.dumps(rule.party1_preferred_jobs, ensure_ascii=False),
                json.dumps(rule.party2_priority_jobs, ensure_ascii=False),
                json.dumps(rule.party2_preferred_jobs, ensure_ascii=False),
            ),
        )

    def update(self, rule: RaidRule) -> None:
        query = """
        UPDATE raid_rules
        SET
            party1_priority_jobs = ?,
            party1_preferred_jobs = ?,
            party2_priority_jobs = ?,
            party2_preferred_jobs = ?
        WHERE guild_id = ? AND channel_id = ? AND raid_name = ?
        """
        self.db.execute(
            query,
            (
                json.dumps(rule.party1_priority_jobs, ensure_ascii=False),
                json.dumps(rule.party1_preferred_jobs, ensure_ascii=False),
                json.dumps(rule.party2_priority_jobs, ensure_ascii=False),
                json.dumps(rule.party2_preferred_jobs, ensure_ascii=False),
                rule.guild_id,
                rule.channel_id,
                rule.raid_name,
            ),
        )

    def upsert(self, rule: RaidRule) -> None:
        existing = self.find_by_channel_and_raid(
            guild_id=rule.guild_id,
            channel_id=rule.channel_id,
            raid_name=rule.raid_name,
        )
        if existing is None:
            self.save(rule)
        else:
            self.update(rule)
