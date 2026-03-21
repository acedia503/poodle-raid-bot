from typing import Optional

from database import Database
from domain.guild_setting import GuildSetting


class GuildSettingRepository:
    def __init__(self, database: Database):
        self.database = database

    def get_by_guild_id(self, guild_id: int) -> Optional[GuildSetting]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, guild_id, default_race, default_server, created_at, updated_at
                FROM guild_settings
                WHERE guild_id = ?
                """,
                (guild_id,),
            ).fetchone()

            if row is None:
                return None

            return GuildSetting(
                id=row["id"],
                guild_id=row["guild_id"],
                default_race=row["default_race"],
                default_server=row["default_server"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def upsert(
        self,
        guild_id: int,
        default_race: str | None,
        default_server: str | None,
    ) -> GuildSetting:
        existing = self.get_by_guild_id(guild_id)

        with self.database.get_connection() as conn:
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO guild_settings (guild_id, default_race, default_server)
                    VALUES (?, ?, ?)
                    """,
                    (guild_id, default_race, default_server),
                )
            else:
                conn.execute(
                    """
                    UPDATE guild_settings
                    SET default_race = ?, default_server = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE guild_id = ?
                    """,
                    (default_race, default_server, guild_id),
                )

        return self.get_by_guild_id(guild_id)

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with self.database.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM guild_settings WHERE guild_id = ?",
                (guild_id,),
            )
            return cursor.rowcount > 0
