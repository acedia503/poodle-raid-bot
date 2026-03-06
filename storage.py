# storage.py
# PostgreSQL 저장 담당


import os
import psycopg2
from models import Character

DATABASE_URL = ${{Postgres.DATABASE_URL}}

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS raids (
        raid_name TEXT PRIMARY KEY,
        min_ilvl INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS raid_members (
        id SERIAL PRIMARY KEY,
        raid_name TEXT,
        user_id BIGINT,
        user_name TEXT,
        character_name TEXT
    );
    """)

    conn.commit()
    cur.close()
    conn.close()


def save_active_raids(active_raids: dict):
    conn = get_conn()
    cur = conn.cursor()

    # 기존 데이터 삭제
    cur.execute("DELETE FROM raids;")
    cur.execute("DELETE FROM raid_members;")

    for raid_name, raid_data in active_raids.items():

        cur.execute(
            "INSERT INTO raids (raid_name, min_ilvl) VALUES (%s,%s)",
            (raid_name, raid_data["min_ilvl"])
        )

        for member in raid_data["members"]:
            cur.execute(
                """
                INSERT INTO raid_members
                (raid_name, user_id, user_name, character_name)
                VALUES (%s,%s,%s,%s)
                """,
                (
                    raid_name,
                    member.user_id,
                    member.user_name,
                    member.name
                )
            )

    conn.commit()
    cur.close()
    conn.close()


def load_active_raids() -> dict:

    init_db()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT raid_name, min_ilvl FROM raids")
    raids = cur.fetchall()

    active_raids = {}

    for raid_name, min_ilvl in raids:
        active_raids[raid_name] = {
            "min_ilvl": min_ilvl,
            "members": []
        }

    cur.execute("""
        SELECT raid_name, user_id, user_name, character_name
        FROM raid_members
    """)

    members = cur.fetchall()

    for raid_name, user_id, user_name, character_name in members:

        if raid_name not in active_raids:
            continue

        active_raids[raid_name]["members"].append(
            Character(
                user_id=user_id,
                user_name=user_name,
                name=character_name
            )
        )

    cur.close()
    conn.close()

    return active_raids
