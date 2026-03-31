# repositories/party_slot_repository.py

from domain.party_slot import PartySlot
from database import Database


class PartySlotRepository:
    def __init__(self, db: Database):
        self.db = db

    # =========================
    # 단건 조회
    # =========================
    def get_by_id(self, slot_id: int):
        query = """
            SELECT *
            FROM party_slots
            WHERE id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (slot_id,))
            return cur.fetchone()

    # =========================
    # 파티 조회
    # =========================
    def get_by_party(self, session_id, group_no, party_no):
        query = """
            SELECT *
            FROM party_slots
            WHERE session_id = %s
              AND group_no = %s
              AND party_no = %s
            ORDER BY slot_no ASC
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (session_id, group_no, party_no))
            return cur.fetchall()

    # =========================
    # 공대 조회
    # =========================
    def get_by_group(self, session_id, group_no):
        query = """
            SELECT *
            FROM party_slots
            WHERE session_id = %s
              AND group_no = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (session_id, group_no))
            return cur.fetchall()

    # =========================
    # INSERT
    # =========================
    def insert(self, slot: PartySlot):
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
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
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

    # =========================
    # DELETE
    # =========================
    def delete_by_id(self, slot_id: int):
        query = """
            DELETE FROM party_slots
            WHERE id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (slot_id,))

    # =========================
    # slot_no 재정렬
    # =========================
    def update_slot_no(self, slot_id: int, slot_no: int):
        query = """
            UPDATE party_slots
            SET slot_no = %s
            WHERE id = %s
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (slot_no, slot_id))
