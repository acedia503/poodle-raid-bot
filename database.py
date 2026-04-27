from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url

    @contextmanager
    def get_connection(self):
        conn = psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.get_connection() as conn:
            cur = conn.cursor()

            # 길드 기본 설정
            cur.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL UNIQUE,
                default_race TEXT NULL,
                default_server TEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 채널별 레이드 설정
            cur.execute("""
            CREATE TABLE IF NOT EXISTS channel_raids (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL UNIQUE,
                raid_name TEXT NOT NULL,
                min_item_level INTEGER NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, raid_name)
            )
            """)
            
            # 캐릭터 정보
            cur.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                race TEXT NOT NULL,
                server TEXT NOT NULL,
                job TEXT NOT NULL,
                item_level INTEGER NOT NULL,
                combat_power INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, character_name, race, server)
            )
            """)
            
            # 레이드 신청
            cur.execute("""
            CREATE TABLE IF NOT EXISTS raid_applications (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                race TEXT NOT NULL,
                server TEXT NOT NULL,
                job TEXT NOT NULL,
                item_level INTEGER NOT NULL,
                combat_power INTEGER NOT NULL,
                raid_name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, raid_name, character_name, race, server)
            )
            """)

            cur.execute("""
            ALTER TABLE raid_applications
            ADD COLUMN IF NOT EXISTS character_id INTEGER
            """)

            # 공대 생성 규칙
            cur.execute("""
            CREATE TABLE IF NOT EXISTS raid_rules (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                raid_name TEXT NOT NULL,
                party1_priority_jobs TEXT NOT NULL DEFAULT '[]',
                party1_preferred_jobs TEXT NOT NULL DEFAULT '[]',
                party2_priority_jobs TEXT NOT NULL DEFAULT '[]',
                party2_preferred_jobs TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, channel_id, raid_name)
            )
            """)

            # 공대 생성 세션
            cur.execute("""
            CREATE TABLE IF NOT EXISTS party_build_sessions (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                raid_name TEXT NOT NULL,
                total_applicants INTEGER NOT NULL,
                full_group_count INTEGER NOT NULL DEFAULT 0,
                temp_group_count INTEGER NOT NULL DEFAULT 0,
                waiting_count INTEGER NOT NULL DEFAULT 0,
                created_by BIGINT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 공대 배치 결과 슬롯
            cur.execute("""
            CREATE TABLE IF NOT EXISTS party_slots (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES party_build_sessions(id) ON DELETE CASCADE,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                raid_name TEXT NOT NULL,
                group_no INTEGER NOT NULL,
                party_no INTEGER NOT NULL,
                slot_no INTEGER NOT NULL,
                is_temp_group BOOLEAN NOT NULL DEFAULT FALSE,
                application_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                job TEXT NOT NULL,
                item_level INTEGER NOT NULL,
                combat_power INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, group_no, party_no, slot_no)
            )
            """)

            # 대기 인원
            cur.execute("""
            CREATE TABLE IF NOT EXISTS party_waiting_members (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES party_build_sessions(id) ON DELETE CASCADE,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                raid_name TEXT NOT NULL,
                application_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                job TEXT NOT NULL,
                item_level INTEGER NOT NULL,
                combat_power INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, user_id, character_name)
            )
            """)

            # 인덱스
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id
            ON guild_settings(guild_id)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_raids_channel_id
            ON channel_raids(channel_id)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_raids_guild_raid
            ON channel_raids(guild_id, raid_name)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_guild_user
            ON raid_applications(guild_id, user_id)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_identity
            ON raid_applications(guild_id, user_id, character_name, race, server)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_raid_lookup
            ON raid_applications(guild_id, raid_name, character_name, race, server)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_rules_lookup
            ON raid_rules(guild_id, channel_id, raid_name)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_party_build_sessions_lookup
            ON party_build_sessions(guild_id, channel_id, raid_name, is_active)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_party_slots_session
            ON party_slots(session_id, group_no, party_no, slot_no)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_party_slots_user
            ON party_slots(session_id, user_id)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_characters_guild_identity
            ON characters(guild_id, character_name, race, server)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_characters_guild_user
            ON characters(guild_id, user_id)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_character_id
            ON raid_applications(character_id)
            """)
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_party_waiting_members_session
            ON party_waiting_members(session_id)
            """)
