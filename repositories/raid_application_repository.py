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
            character_id=row.get("character_id"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def create(self, application: RaidApplication) -> RaidApplication:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO raid_applications (
                    guild_id, channel_id, user_id, user_name,
                    character_name, race, server,
                    job, item_level, combat_power, raid_name,
                    character_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    application.character_id,
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

    def bulk_update_character_snapshots(
        self,
        updates: list[dict],
    ) -> int:
        """
        updates 예시:
        [
            {
                "application_id": 1,
                "job": "수호성",
                "item_level": 3394,
                "combat_power": 247499,
            },
            ...
        ]
        """
        if not updates:
            return 0

        updated_count = 0

        with self.database.get_connection() as conn:
            cur = conn.cursor()

            for item in updates:
                cur.execute(
                    """
                    UPDATE raid_applications
                    SET
                        job = %s,
                        item_level = %s,
                        combat_power = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        item["job"],
                        item["item_level"],
                        item["combat_power"],
                        item["application_id"],
                    ),
                )
                updated_count += cur.rowcount

        return updated_count

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

    def count_by_guild_and_raid_name(
        self,
        guild_id: int,
        raid_name: str,
    ) -> int:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM raid_applications
                WHERE guild_id = %s
                  AND raid_name = %s
                """,
                (guild_id, raid_name),
            )
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0

    def delete_by_guild_and_raid_name(
        self,
        guild_id: int,
        raid_name: str,
    ) -> int:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM raid_applications
                WHERE guild_id = %s
                  AND raid_name = %s
                """,
                (guild_id, raid_name),
            )
            return cur.rowcount

    def get_by_guild_and_raid_name(
        self,
        guild_id: int,
        raid_name: str,
    ) -> list[RaidApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = %s
                  AND raid_name = %s
                ORDER BY created_at ASC
                """,
                (guild_id, raid_name),
            )
            rows = cur.fetchall()
            return [self._to_domain(row) for row in rows]

    def get_by_guild_raid_and_user_id(
        self,
        guild_id: int,
        raid_name: str,
        user_id: int,
    ) -> list[RaidApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = %s
                  AND raid_name = %s
                  AND user_id = %s
                ORDER BY created_at ASC
                """,
                (guild_id, raid_name, user_id),
            )
            rows = cur.fetchall()
            return [self._to_domain(row) for row in rows]

    def get_by_guild_raid_and_character_name(
        self,
        guild_id: int,
        raid_name: str,
        character_name: str,
    ) -> list[RaidApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM raid_applications
                WHERE guild_id = %s
                  AND raid_name = %s
                  AND character_name = %s
                ORDER BY created_at ASC
                """,
                (guild_id, raid_name, character_name),
            )
            rows = cur.fetchall()
            return [self._to_domain(row) for row in rows]

    def delete_by_ids(self, application_ids: list[int]) -> int:
        if not application_ids:
            return 0

        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM raid_applications
                WHERE id = ANY(%s)
                """,
                (application_ids,),
            )
            return cur.rowcount

    def get_by_guild_channel_and_raid(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
    ) -> list[RaidApplication]:
        query = """
            SELECT *
            FROM raid_applications
            WHERE guild_id = %s
              AND channel_id = %s
              AND raid_name = %s
            ORDER BY created_at ASC
        """
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (guild_id, channel_id, raid_name))
            rows = cur.fetchall()

        return [self._to_domain(row) for row in rows]

    def update_character_snapshot(
        self,
        application_id: int,
        job: str,
        item_level: int,
        combat_power: int,
    ) -> None:
        query = """
            UPDATE raid_applications
            SET
                job = %s,
                item_level = %s,
                combat_power = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (job, item_level, combat_power, application_id))

    def search_distinct_users_by_guild_raid_and_keyword(
        self,
        guild_id: int,
        raid_name: str,
        keyword: str,
    ) -> list[dict]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT user_id, user_name
                FROM raid_applications
                WHERE guild_id = %s
                  AND raid_name = %s
                  AND LOWER(user_name) LIKE %s
                ORDER BY user_name ASC
                """,
                (guild_id, raid_name, f"%{keyword.lower()}%"),
            )
            return cur.fetchall()
