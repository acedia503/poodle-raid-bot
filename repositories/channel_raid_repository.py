from typing import Optional

from database import Database
from domain.channel_raid import ChannelRaid


class ChannelRaidRepository:
    def __init__(self, database: Database):
        self.database = database

    def get_active_by_channel_id(self, channel_id: int) -> Optional[ChannelRaid]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM channel_raids
                WHERE channel_id = ? AND is_active = 1
                """,
                (channel_id,),
            ).fetchone()

            if row is None:
                return None

            return ChannelRaid(
                id=row["id"],
                guild_id=row["guild_id"],
                channel_id=row["channel_id"],
                raid_name=row["raid_name"],
                min_item_level=row["min_item_level"],
                min_combat_power=row["min_combat_power"],
                entry_condition_text=row["entry_condition_text"],
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def get_by_guild_and_raid_name(self, guild_id: int, raid_name: str) -> Optional[ChannelRaid]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM channel_raids
                WHERE guild_id = ? AND raid_name = ? AND is_active = 1
                """,
                (guild_id, raid_name),
            ).fetchone()

            if row is None:
                return None

            return ChannelRaid(
                id=row["id"],
                guild_id=row["guild_id"],
                channel_id=row["channel_id"],
                raid_name=row["raid_name"],
                min_item_level=row["min_item_level"],
                min_combat_power=row["min_combat_power"],
                entry_condition_text=row["entry_condition_text"],
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def upsert(self, channel_raid: ChannelRaid) -> ChannelRaid:
        existing = self.get_active_by_channel_id(channel_raid.channel_id)

        with self.database.get_connection() as conn:
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO channel_raids (
                        guild_id, channel_id, raid_name, min_item_level,
                        min_combat_power, entry_condition_text, is_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        channel_raid.guild_id,
                        channel_raid.channel_id,
                        channel_raid.raid_name,
                        channel_raid.min_item_level,
                        channel_raid.min_combat_power,
                        channel_raid.entry_condition_text,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE channel_raids
                    SET raid_name = ?, min_item_level = ?, min_combat_power = ?,
                        entry_condition_text = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE channel_id = ?
                    """,
                    (
                        channel_raid.raid_name,
                        channel_raid.min_item_level,
                        channel_raid.min_combat_power,
                        channel_raid.entry_condition_text,
                        channel_raid.channel_id,
                    ),
                )

        return self.get_active_by_channel_id(channel_raid.channel_id)

    def delete_by_channel_id(self, channel_id: int) -> bool:
        with self.database.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM channel_raids WHERE channel_id = ?",
                (channel_id,),
            )
            return cursor.rowcount > 0
