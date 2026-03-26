from domain.party_slot import PartySlot
from database import Database


class PartySlotRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_all(self, slots: list[PartySlot]) -> None:
        if not slots:
            return

        query = """
            INSERT INTO party_slots (
                session_id,
                guild_id,
                channel_id,
                raid_name,
                group_no,
                party_no,
                slot_no,
                is_temp_group,
                application_id,
                user_id,
                user_name,
                character_name,
                job,
                item_level,
                combat_power
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, group_no, party_no, slot_no)
            DO NOTHING
        """

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            for slot in slots:
                cur.execute(
                    query,
                    (
                        slot.session_id,
                        slot.guild_id,
                        slot.channel_id,
                        slot.raid_name,
                        slot.group_no,
                        slot.party_no,
                        slot.slot_no,
                        slot.is_temp_group,
                        slot.application_id,
                        slot.user_id,
                        slot.user_name,
                        slot.character_name,
                        slot.job,
                        slot.item_level,
                        slot.combat_power,
                    ),
                )

    def get_by_session_id(self, session_id: int) -> list[dict]:
        query = """
            SELECT *
            FROM party_slots
            WHERE session_id = %s
            ORDER BY group_no, party_no, slot_no
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (session_id,))
            return cur.fetchall()

    def get_by_id(self, slot_id: int) -> dict | None:
        query = """
            SELECT *
            FROM party_slots
            WHERE id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (slot_id,))
            return cur.fetchone()

    def delete_by_id(self, slot_id: int) -> None:
        query = """
            DELETE FROM party_slots
            WHERE id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (slot_id,))

    def update_slot_member(
        self,
        slot_id: int,
        application_id: int,
        user_id: int,
        user_name: str,
        character_name: str,
        job: str,
        item_level: int,
        combat_power: int,
    ) -> None:
        query = """
            UPDATE party_slots
            SET
                application_id = %s,
                user_id = %s,
                user_name = %s,
                character_name = %s,
                job = %s,
                item_level = %s,
                combat_power = %s
            WHERE id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (
                    application_id,
                    user_id,
                    user_name,
                    character_name,
                    job,
                    item_level,
                    combat_power,
                    slot_id,
                ),
            )

    def insert_slot(
        self,
        session_id: int,
        guild_id: int,
        channel_id: int,
        raid_name: str,
        group_no: int,
        party_no: int,
        slot_no: int,
        is_temp_group: bool,
        application_id: int,
        user_id: int,
        user_name: str,
        character_name: str,
        job: str,
        item_level: int,
        combat_power: int,
    ) -> None:
        query = """
            INSERT INTO party_slots (
                session_id,
                guild_id,
                channel_id,
                raid_name,
                group_no,
                party_no,
                slot_no,
                is_temp_group,
                application_id,
                user_id,
                user_name,
                character_name,
                job,
                item_level,
                combat_power
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, group_no, party_no, slot_no)
            DO NOTHING
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
                    group_no,
                    party_no,
                    slot_no,
                    is_temp_group,
                    application_id,
                    user_id,
                    user_name,
                    character_name,
                    job,
                    item_level,
                    combat_power,
                ),
            )

    def count_party_members(
        self,
        session_id: int,
        group_no: int,
        party_no: int,
    ) -> int:
        query = """
            SELECT COUNT(*) AS cnt
            FROM party_slots
            WHERE session_id = %s
              AND group_no = %s
              AND party_no = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (session_id, group_no, party_no))
            row = cur.fetchone()
            return row["cnt"]

    def get_next_slot_no(
        self,
        session_id: int,
        group_no: int,
        party_no: int,
    ) -> int:
        query = """
            SELECT COALESCE(MAX(slot_no), 0) + 1 AS next_slot_no
            FROM party_slots
            WHERE session_id = %s
              AND group_no = %s
              AND party_no = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (session_id, group_no, party_no))
            row = cur.fetchone()
            return row["next_slot_no"]

    def reorder_party_slots(
        self,
        session_id: int,
        group_no: int,
        party_no: int,
    ) -> None:
        rows = self.get_by_session_id(session_id)
        target_rows = [
            row for row in rows
            if row["group_no"] == group_no and row["party_no"] == party_no
        ]
        target_rows.sort(key=lambda x: x["slot_no"])

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            for idx, row in enumerate(target_rows, start=1):
                cur.execute(
                    """
                    UPDATE party_slots
                    SET slot_no = %s
                    WHERE id = %s
                    """,
                    (idx, row["id"]),
                )
