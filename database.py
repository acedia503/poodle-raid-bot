import psycopg2


class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def get_connection(self):
        return psycopg2.connect(self.database_url)

    def initialize(self):
        conn = self.get_connection()
        cur = conn.cursor()

        # 길드 설정
        cur.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT UNIQUE,
            default_race TEXT,
            default_server TEXT
        )
        """)

        # 채널 레이드
        cur.execute("""
        CREATE TABLE IF NOT EXISTS channel_raids (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT,
            channel_id BIGINT UNIQUE,
            raid_name TEXT,
            min_item_level INT
        )
        """)

        # 레이드 신청
        cur.execute("""
        CREATE TABLE IF NOT EXISTS raid_applications (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT,
            channel_id BIGINT,
            user_id BIGINT,
            user_name TEXT,
            character_name TEXT,
            race TEXT,
            server TEXT,
            job TEXT,
            item_level INT,
            combat_power INT,
            raid_name TEXT
        )
        """)

        conn.commit()
        cur.close()
        conn.close()
