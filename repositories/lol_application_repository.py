from typing import Optional

from database import Database
from models.lol_application import LolApplication


class LolApplicationRepository:
    def __init__(self, database: Database):
        self.database = database

    def _to_domain(self, row) -> LolApplication:
        return LolApplication(
            id=row["id"],
            guild_id=row["guild_id"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            riot_id=row["riot_id"],
            normalized_riot_id=row["normalized_riot_id"],
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _get_by_id(self, application_id: int) -> Optional[LolApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM lol_applications
                WHERE id = %s
                """,
                (application_id,),
            )
            row = cur.fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def get_by_guild_and_user_id(
        self,
        guild_id: int,
        user_id: int,
    ) -> Optional[LolApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM lol_applications
                WHERE guild_id = %s
                  AND user_id = %s
                """,
                (guild_id, user_id),
            )
            row = cur.fetchone()

            if row is None:
                return None
            return self._to_domain(row)

    def get_all_by_guild_id(self, guild_id: int) -> list[LolApplication]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM lol_applications
                WHERE guild_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (guild_id,),
            )
            rows = cur.fetchall()
            return [self._to_domain(row) for row in rows]

    def exists_by_normalized_riot_id(
        self,
        guild_id: int,
        normalized_riot_id: str,
        exclude_user_id: Optional[int] = None,
    ) -> bool:
        with self.database.get_connection() as conn:
            cur = conn.cursor()

            if exclude_user_id is None:
                cur.execute(
                    """
                    SELECT 1
                    FROM lol_applications
                    WHERE guild_id = %s
                      AND normalized_riot_id = %s
                    LIMIT 1
                    """,
                    (guild_id, normalized_riot_id),
                )
            else:
                cur.execute(
                    """
                    SELECT 1
                    FROM lol_applications
                    WHERE guild_id = %s
                      AND normalized_riot_id = %s
                      AND user_id != %s
                    LIMIT 1
                    """,
                    (guild_id, normalized_riot_id, exclude_user_id),
                )

            return cur.fetchone() is not None

    def upsert(
        self,
        guild_id: int,
        user_id: int,
        user_name: str,
        riot_id: str,
        normalized_riot_id: str,
    ) -> tuple[LolApplication, bool]:
        """
        (guild_id, user_id) 기준으로 신규 등록 또는 기존 신청 수정을 처리한다.
        반환값: (LolApplication, is_new)
        """
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO lol_applications (
                    guild_id, user_id, user_name, riot_id, normalized_riot_id
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET
                    user_name = EXCLUDED.user_name,
                    riot_id = EXCLUDED.riot_id,
                    normalized_riot_id = EXCLUDED.normalized_riot_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, (xmax = 0) AS is_new
                """,
                (guild_id, user_id, user_name, riot_id, normalized_riot_id),
            )
            row = cur.fetchone()
            application_id = row["id"]
            is_new = bool(row["is_new"])

        application = self._get_by_id(application_id)
        return application, is_new

    def delete_by_guild_and_user_id(self, guild_id: int, user_id: int) -> bool:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM lol_applications
                WHERE guild_id = %s
                  AND user_id = %s
                """,
                (guild_id, user_id),
            )
            return cur.rowcount > 0

    def delete_all_by_guild_id(self, guild_id: int) -> int:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM lol_applications
                WHERE guild_id = %s
                """,
                (guild_id,),
            )
            return cur.rowcount

    def count_by_guild_id(self, guild_id: int) -> int:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM lol_applications
                WHERE guild_id = %s
                """,
                (guild_id,),
            )
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0
