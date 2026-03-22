from typing import Optional

from database import Database
from domain.guild_setting import GuildSetting


class GuildSettingRepository:
    def __init__(self, database: Database):
        self.database = database

    def get_by_guild_id(self, guild_id: int) -> Optional[GuildSetting]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, guild_id, default_race, default_server, created_at, updated_at
                FROM guild_settings
                WHERE guild_id = %s
                """,
                (guild_id,),
            )
            row = cur.fetchone()

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
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO guild_settings (guild_id, default_race, default_server)
                VALUES (%s, %s, %s)
                ON CONFLICT (guild_id)
                DO UPDATE SET
                    default_race = EXCLUDED.default_race,
                    default_server = EXCLUDED.default_server,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (guild_id, default_race, default_server),
            )
            cur.fetchone()

        return self.get_by_guild_id(guild_id)

    def delete_by_guild_id(self, guild_id: int) -> bool:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM guild_settings WHERE guild_id = %s",
                (guild_id,),
            )
            return cur.rowcount > 0
