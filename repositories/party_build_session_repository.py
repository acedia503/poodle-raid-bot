from domain.party_build_session import PartyBuildSession
from database import Database


class PartyBuildSessionRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_active_session(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
    ) -> PartyBuildSession | None:
        query = """
            SELECT *
            FROM party_build_sessions
            WHERE guild_id = %s
              AND channel_id = %s
              AND raid_name = %s
              AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (guild_id, channel_id, raid_name))
            row = cur.fetchone()

        if row is None:
            return None

        return PartyBuildSession(
            id=row["id"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            raid_name=row["raid_name"],
            total_applicants=row["total_applicants"],
            full_group_count=row["full_group_count"],
            temp_group_count=row["temp_group_count"],
            waiting_count=row["waiting_count"],
            created_by=row["created_by"],
            is_active=row["is_active"],
        )

    def deactivate_existing_sessions(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
    ) -> None:
        query = """
            UPDATE party_build_sessions
            SET is_active = FALSE
            WHERE guild_id = %s
              AND channel_id = %s
              AND raid_name = %s
              AND is_active = TRUE
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (guild_id, channel_id, raid_name))

    def save(self, session: PartyBuildSession) -> PartyBuildSession:
        query = """
            INSERT INTO party_build_sessions (
                guild_id,
                channel_id,
                raid_name,
                total_applicants,
                full_group_count,
                temp_group_count,
                waiting_count,
                created_by,
                is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (
                    session.guild_id,
                    session.channel_id,
                    session.raid_name,
                    session.total_applicants,
                    session.full_group_count,
                    session.temp_group_count,
                    session.waiting_count,
                    session.created_by,
                    session.is_active,
                ),
            )
            row = cur.fetchone()

        session.id = row["id"]
        return session
