from typing import Optional

from database import Database
from domain.enums import ApplicationStatus, SourceType
from domain.raid_application import RaidApplication


class RaidApplicationRepository:
    def __init__(self, database: Database):
        self.database = database

    def _to_domain(self, row) -> RaidApplication:
        return RaidApplication(
            id=row["id"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            raid_name=row["raid_name"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            character_name=row["character_name"],
            job=row["job"],
            item_level=row["item_level"],
            combat_power=row["combat_power"],
            application_status=ApplicationStatus(row["application_status"]),
            source_type=SourceType(row["source_type"]),
            created_by_user_id=row["created_by_user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(self, application: RaidApplication) -> RaidApplication:
        with self.database.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO raid_applications (
                    guild_id, channel_id, raid_name, user_id, user_name,
                    character_name, job, item_level, combat_power,
                    application_status, source_type, created_by_user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    application.guild_id,
                    application.channel_id,
                    application.raid_name,
                    application.user_id,
                    application.user_name,
                    application.character_name,
                    application.job,
                    application.item_level,
                    application.combat_power,
                    application.application_status.value,
                    application.source_type.value,
                    application.created_by_user_id,
                ),
            )
            application_id = cursor.lastrowid

        return self.get_by_id(application_id)

    def get_by_id(self, application_id: int) -> Optional[RaidApplication]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM raid_applications WHERE id = ?",
                (application_id,),
            ).fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def delete_by_id(self, application_id: int) -> bool:
        with self.database.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM raid_applications WHERE id = ?",
                (application_id,),
            )
            return cursor.rowcount > 0

    def get_by_guild_raid_character(
        self,
        guild_id: int,
        raid_name: str,
        character_name: str,
    ) -> Optional[RaidApplication]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = ? AND raid_name = ? AND character_name = ?
                """,
                (guild_id, raid_name, character_name),
            ).fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def get_user_application_in_raid(
        self,
        guild_id: int,
        user_id: int,
        raid_name: str,
    ) -> list[RaidApplication]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = ? AND user_id = ? AND raid_name = ?
                ORDER BY created_at DESC
                """,
                (guild_id, user_id, raid_name),
            ).fetchall()

            return [self._to_domain(row) for row in rows]

    def get_user_applications(self, guild_id: int, user_id: int) -> list[RaidApplication]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = ? AND user_id = ?
                ORDER BY created_at DESC
                """,
                (guild_id, user_id),
            ).fetchall()

            return [self._to_domain(row) for row in rows]
