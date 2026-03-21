import sqlite3
from contextlib import contextmanager


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
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
            cursor = conn.cursor()

            # 길드 기본 설정
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL UNIQUE,
                default_race TEXT NULL,
                default_server TEXT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 채널 레이드 설정
            # 규칙:
            # - channel_id는 1채널 1레이드
            # - 같은 guild 안에서 동일 raid_name 중복 금지
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_raids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL UNIQUE,
                raid_name TEXT NOT NULL,
                min_item_level INTEGER NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, raid_name)
            )
            """)

            # 신청 데이터
            # 중복 기준:
            # 동일 길드 + 동일 레이드 + 동일 캐릭터명 + 동일 종족 + 동일 서버
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS raid_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                race TEXT NOT NULL,
                server TEXT NOT NULL,
                job TEXT NOT NULL,
                item_level INTEGER NOT NULL,
                combat_power INTEGER NOT NULL,
                raid_name TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, raid_name, character_name, race, server)
            )
            """)

            # 인덱스
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id
            ON guild_settings(guild_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_raids_channel_id
            ON channel_raids(channel_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_raids_guild_raid
            ON channel_raids(guild_id, raid_name)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_guild_user
            ON raid_applications(guild_id, user_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_character_identity
            ON raid_applications(guild_id, user_id, character_name, race, server)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_raid_lookup
            ON raid_applications(guild_id, raid_name, character_name, race, server)
            """)
