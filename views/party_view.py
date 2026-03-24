import json
from typing import Optional

from domain.raid_rule import RaidRule
from utils.constants import JOB_OPTIONS
from database import Database


class RaidRuleRepository:
    def __init__(self, db: Database):
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
            WHERE guild_id = %s
              AND channel_id = %s
              AND raid_name = %s
        """

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (guild_id, channel_id, raid_name))
            row = cur.fetchone()

        if row is None:
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
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
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
                party1_priority_jobs = %s,
                party1_preferred_jobs = %s,
                party2_priority_jobs = %s,
                party2_preferred_jobs = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = %s
              AND channel_id = %s
              AND raid_name = %s
        """

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
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
        query = """
            INSERT INTO raid_rules (
                guild_id,
                channel_id,
                raid_name,
                party1_priority_jobs,
                party1_preferred_jobs,
                party2_priority_jobs,
                party2_preferred_jobs
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (guild_id, channel_id, raid_name)
            DO UPDATE SET
                party1_priority_jobs = EXCLUDED.party1_priority_jobs,
                party1_preferred_jobs = EXCLUDED.party1_preferred_jobs,
                party2_priority_jobs = EXCLUDED.party2_priority_jobs,
                party2_preferred_jobs = EXCLUDED.party2_preferred_jobs,
                updated_at = CURRENT_TIMESTAMP
        """

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
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
