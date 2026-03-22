from typing import Optional

from database import Database
from domain.channel_raid import ChannelRaid


class ChannelRaidRepository:
    def __init__(self, database: Database):
        self.database = database

    def _to_domain(self, row) -> ChannelRaid:
        return ChannelRaid(
            id=row["id"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            raid_name=row["raid_name"],
            min_item_level=row["min_item_level"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_active_by_channel_id(self, channel_id: int) -> Optional[ChannelRaid]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM channel_raids
                WHERE channel_id = %s AND is_active = TRUE
                """,
                (channel_id,),
            )
            row = cur.fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def get_by_guild_and_raid_name(self, guild_id: int, raid_name: str) -> Optional[ChannelRaid]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM channel_raids
                WHERE guild_id = %s AND raid_name = %s AND is_active = TRUE
                """,
                (guild_id, raid_name),
            )
            row = cur.fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def upsert(self, channel_raid: ChannelRaid) -> ChannelRaid:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO channel_raids (
                    guild_id, channel_id, raid_name, min_item_level, is_active
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (channel_id)
                DO UPDATE SET
                    raid_name = EXCLUDED.raid_name,
                    min_item_level = EXCLUDED.min_item_level,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (
                    channel_raid.guild_id,
                    channel_raid.channel_id,
                    channel_raid.raid_name,
                    channel_raid.min_item_level,
                    channel_raid.is_active,
                ),
            )
            cur.fetchone()

        return self.get_active_by_channel_id(channel_raid.channel_id)

    def delete_by_channel_id(self, channel_id: int) -> bool:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM channel_raids WHERE channel_id = %s",
                (channel_id,),
            )
            return cur.rowcount > 0
