from typing import Optional

from database import Database
from domain.raid_application import RaidApplication


class RaidApplicationRepository:
    def __init__(self, database: Database):
        self.database = database

    def _to_domain(self, row) -> RaidApplication:
        return RaidApplication(
            id=row["id"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            character_name=row["character_name"],
            race=row["race"],
            server=row["server"],
            job=row["job"],
            item_level=row["item_level"],
            combat_power=row["combat_power"],
            raid_name=row["raid_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(self, application: RaidApplication) -> RaidApplication:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO raid_applications (
                    guild_id, channel_id, user_id, user_name,
                    character_name, race, server,
                    job, item_level, combat_power, raid_name
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    application.guild_id,
                    application.channel_id,
                    application.user_id,
                    application.user_name,
                    application.character_name,
                    application.race,
                    application.server,
                    application.job,
                    application.item_level,
                    application.combat_power,
                    application.raid_name,
                ),
            )
            application_id = cur.fetchone()["id"]

        return self.get_by_id(application_id)

    def get_by_id(self, application_id: int) -> Optional[RaidApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE id = %s
                """,
                (application_id,),
            )
            row = cur.fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def get_by_guild_raid_character_identity(
        self,
        guild_id: int,
        raid_name: str,
        character_name: str,
        race: str,
        server: str,
    ) -> Optional[RaidApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = %s
                  AND raid_name = %s
                  AND character_name = %s
                  AND race = %s
                  AND server = %s
                """,
                (guild_id, raid_name, character_name, race, server),
            )
            row = cur.fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def get_user_application_in_raid(
        self,
        guild_id: int,
        user_id: int,
        character_name: str,
        race: str,
        server: str,
        raid_name: str,
    ) -> Optional[RaidApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = %s
                  AND user_id = %s
                  AND character_name = %s
                  AND race = %s
                  AND server = %s
                  AND raid_name = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (guild_id, user_id, character_name, race, server, raid_name),
            )
            row = cur.fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def get_user_applications_by_character_identity(
        self,
        guild_id: int,
        user_id: int,
        character_name: str,
        race: str,
        server: str,
    ) -> list[RaidApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = %s
                  AND user_id = %s
                  AND character_name = %s
                  AND race = %s
                  AND server = %s
                ORDER BY created_at DESC
                """,
                (guild_id, user_id, character_name, race, server),
            )
            rows = cur.fetchall()

            return [self._to_domain(row) for row in rows]

    def bulk_update_character_snapshot(
        self,
        applications: list[RaidApplication],
        job: str,
        item_level: int,
        combat_power: int,
    ) -> int:
        if not applications:
            return 0

        ids = [app.id for app in applications if app.id is not None]
        if not ids:
            return 0

        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE raid_applications
                SET job = %s,
                    item_level = %s,
                    combat_power = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ANY(%s)
                """,
                (job, item_level, combat_power, ids),
            )
            return cur.rowcount

    def delete_by_id(self, application_id: int) -> bool:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM raid_applications
                WHERE id = %s
                """,
                (application_id,),
            )
            return cur.rowcount > 0
