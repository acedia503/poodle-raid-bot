from typing import List

from database import Database
from domain.raid_application import RaidApplication


class RaidApplicationRepository:
    def __init__(self, database: Database):
        self.database = database

    def get_user_applications_by_character_identity(
        self,
        guild_id: int,
        user_id: int,
        character_name: str,
        race: str,
        server: str,
    ) -> List[RaidApplication]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = ?
                  AND user_id = ?
                  AND character_name = ?
                  AND race = ?
                  AND server = ?
                """,
                (guild_id, user_id, character_name, race, server),
            ).fetchall()

            return [RaidApplication(**row) for row in rows]

    def get_user_application_in_raid(
        self,
        guild_id: int,
        user_id: int,
        character_name: str,
        race: str,
        server: str,
        raid_name: str,
    ):
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = ?
                  AND user_id = ?
                  AND character_name = ?
                  AND race = ?
                  AND server = ?
                  AND raid_name = ?
                """,
                (guild_id, user_id, character_name, race, server, raid_name),
            ).fetchone()

            return RaidApplication(**row) if row else None

    def create(self, application: RaidApplication) -> RaidApplication:
        with self.database.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO raid_applications (
                    guild_id, channel_id, user_id, user_name,
                    character_name, race, server,
                    job, item_level, combat_power, raid_name
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            application.id = cursor.lastrowid
            return application

    def bulk_update_character_snapshot(
        self,
        applications: List[RaidApplication],
        job: str,
        item_level: int,
        combat_power: int,
    ):
        if not applications:
            return

        ids = [app.id for app in applications]

        with self.database.get_connection() as conn:
            conn.executemany(
                """
                UPDATE raid_applications
                SET job = ?, item_level = ?, combat_power = ?
                WHERE id = ?
                """,
                [(job, item_level, combat_power, app_id) for app_id in ids],
            )
