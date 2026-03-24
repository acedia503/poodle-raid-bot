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
