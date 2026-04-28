from typing import Optional

from database import Database
from domain.character import Character


class CharacterRepository:
    def __init__(self, database: Database):
        self.database = database

    def _to_domain(self, row) -> Character:
        return Character(
            id=row["id"],
            guild_id=row["guild_id"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            character_name=row["character_name"],
            race=row["race"],
            server=row["server"],
            job=row["job"],
            item_level=row["item_level"],
            combat_power=row["combat_power"],
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def get_by_identity(
        self,
        guild_id: int,
        character_name: str,
        race: str,
        server: str,
    ) -> Optional[Character]:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM characters
                WHERE guild_id = %s
                  AND character_name = %s
                  AND race = %s
                  AND server = %s
                """,
                (guild_id, character_name, race, server),
            )
            row = cur.fetchone()
            return self._to_domain(row) if row else None

    def upsert(
        self,
        guild_id: int,
        user_id: int,
        user_name: str,
        character_name: str,
        race: str,
        server: str,
        job: str,
        item_level: int,
        combat_power: int,
    ) -> Character:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO characters (
                    guild_id, user_id, user_name,
                    character_name, race, server,
                    job, item_level, combat_power
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (guild_id, character_name, race, server)
                DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    user_name = EXCLUDED.user_name,
                    job = EXCLUDED.job,
                    item_level = EXCLUDED.item_level,
                    combat_power = EXCLUDED.combat_power,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
                """,
                (
                    guild_id,
                    user_id,
                    user_name,
                    character_name,
                    race,
                    server,
                    job,
                    item_level,
                    combat_power,
                ),
            )
            row = cur.fetchone()
            return self._to_domain(row)
            print("[APP][CHARACTER]", character)
            
    def delete_by_id(self, character_id: int) -> bool:
        with self.database.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM characters
                WHERE id = %s
                """,
                (character_id,),
            )
            return cur.rowcount > 0
