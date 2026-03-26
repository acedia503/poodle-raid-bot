from domain.party_waiting_member import PartyWaitingMember
from database import Database


class PartyWaitingMemberRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_all(self, waiting_members: list[PartyWaitingMember]) -> None:
        if not waiting_members:
            return

        query = """
            INSERT INTO party_waiting_members (
                session_id,
                guild_id,
                channel_id,
                raid_name,
                application_id,
                user_id,
                user_name,
                character_name,
                job,
                item_level,
                combat_power
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            for member in waiting_members:
                cur.execute(
                    query,
                    (
                        member.session_id,
                        member.guild_id,
                        member.channel_id,
                        member.raid_name,
                        member.application_id,
                        member.user_id,
                        member.user_name,
                        member.character_name,
                        member.job,
                        member.item_level,
                        member.combat_power,
                    ),
                )

    def get_by_session_id(self, session_id: int) -> list[dict]:
        query = """
            SELECT *
            FROM party_waiting_members
            WHERE session_id = %s
            ORDER BY combat_power DESC, character_name ASC
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (session_id,))
            return cur.fetchall()

    def get_by_id(self, waiting_id: int) -> dict | None:
        query = """
            SELECT *
            FROM party_waiting_members
            WHERE id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (waiting_id,))
            return cur.fetchone()

    def delete_by_id(self, waiting_id: int) -> None:
        query = """
            DELETE FROM party_waiting_members
            WHERE id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (waiting_id,))

    def insert_waiting(
        self,
        session_id: int,
        guild_id: int,
        channel_id: int,
        raid_name: str,
        application_id: int,
        user_id: int,
        user_name: str,
        character_name: str,
        job: str,
        item_level: int,
        combat_power: int,
    ) -> None:
        query = """
            INSERT INTO party_waiting_members (
                session_id,
                guild_id,
                channel_id,
                raid_name,
                application_id,
                user_id,
                user_name,
                character_name,
                job,
                item_level,
                combat_power
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (
                    session_id,
                    guild_id,
                    channel_id,
                    raid_name,
                    application_id,
                    user_id,
                    user_name,
                    character_name,
                    job,
                    item_level,
                    combat_power,
                ),
            )

    def count_by_session_id(self, session_id: int) -> int:
        query = """
            SELECT COUNT(*) AS cnt
            FROM party_waiting_members
            WHERE session_id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (session_id,))
            row = cur.fetchone()
            return row["cnt"]
