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

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_raids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL UNIQUE,
                raid_name TEXT NOT NULL,
                min_item_level INTEGER NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS raid_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                raid_name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                job TEXT NOT NULL,
                item_level INTEGER NOT NULL,
                combat_power INTEGER NOT NULL,
                application_status TEXT NOT NULL DEFAULT 'applied',
                source_type TEXT NOT NULL DEFAULT 'user',
                created_by_user_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, raid_name, character_name)
            )
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_guild_user
            ON raid_applications(guild_id, user_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_applications_raid_status
            ON raid_applications(raid_name, application_status)
            """)
