# storage.py
# PostgreSQL 저장 담당 (Railway 안전 버전)

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from models import Character


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return database_url


def get_conn():
    database_url = get_database_url()
    return psycopg2.connect(database_url, sslmode="require")


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS raids (
            raid_name TEXT PRIMARY KEY,
            min_ilvl INTEGER NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS raid_members (
            id SERIAL PRIMARY KEY,
            raid_name TEXT NOT NULL,
            user_id BIGINT NOT NULL,
            user_name TEXT NOT NULL,
            character_name TEXT NOT NULL
        );
        """)

        conn.commit()
    finally:
        cur.close()
        conn.close()


def save_active_raids(active_raids: dict):
    conn = get_conn()
    cur = conn.cursor()

    try:
        # 전체 저장 방식: 기존 데이터 비우고 다시 저장
        cur.execute("DELETE FROM raid_members;")
        cur.execute("DELETE FROM raids;")

        for raid_name, raid_data in active_raids.items():
            min_ilvl = raid_data.get("min_ilvl", 0)
            members = raid_data.get("members", [])

            cur.execute(
                """
                INSERT INTO raids (raid_name, min_ilvl)
                VALUES (%s, %s)
                """,
                (raid_name, min_ilvl)
            )

            for member in members:
                cur.execute(
                    """
                    INSERT INTO raid_members
                    (raid_name, user_id, user_name, character_name)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        raid_name,
                        member.user_id,
                        member.user_name,
                        member.name
                    )
                )

        conn.commit()
    finally:
        cur.close()
        conn.close()


def load_active_raids() -> dict:
    init_db()

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        active_raids = {}

        cur.execute("""
            SELECT raid_name, min_ilvl
            FROM raids
            ORDER BY raid_name
        """)
        raid_rows = cur.fetchall()

        for row in raid_rows:
            active_raids[row["raid_name"]] = {
                "min_ilvl": row["min_ilvl"],
                "members": []
            }

        cur.execute("""
            SELECT raid_name, user_id, user_name, character_name
            FROM raid_members
            ORDER BY id
        """)
        member_rows = cur.fetchall()

        for row in member_rows:
            raid_name = row["raid_name"]

            if raid_name not in active_raids:
                continue

            active_raids[raid_name]["members"].append(
                Character(
                    user_id=row["user_id"],
                    user_name=row["user_name"],
                    name=row["character_name"]
                )
            )

        return active_raids

    finally:
        cur.close()
        conn.close()
