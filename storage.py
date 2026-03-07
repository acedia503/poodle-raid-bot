# storage.py
# PostgreSQL 저장 담당 (레이드 + 신청목록 + 공대결과)

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
    return psycopg2.connect(get_database_url(), sslmode="require")


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    try:
        # 레이드 기본 정보
        cur.execute("""
        CREATE TABLE IF NOT EXISTS raids (
            raid_name TEXT PRIMARY KEY,
            min_ilvl INTEGER NOT NULL
        );
        """)

        # 신청자 목록
        cur.execute("""
        CREATE TABLE IF NOT EXISTS raid_members (
            id SERIAL PRIMARY KEY,
            raid_name TEXT NOT NULL,
            user_id BIGINT NOT NULL,
            user_name TEXT NOT NULL,
            character_name TEXT NOT NULL
        );
        """)

        # 저장된 공대 정보 (공대 번호)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS raid_parties (
            id SERIAL PRIMARY KEY,
            raid_name TEXT NOT NULL,
            raid_no INTEGER NOT NULL
        );
        """)

        # 저장된 공대 멤버 정보
        cur.execute("""
        CREATE TABLE IF NOT EXISTS raid_party_members (
            id SERIAL PRIMARY KEY,
            raid_name TEXT NOT NULL,
            raid_no INTEGER NOT NULL,
            party_name TEXT NOT NULL,
            position_order INTEGER NOT NULL,
            user_id BIGINT NOT NULL,
            user_name TEXT NOT NULL,
            character_name TEXT NOT NULL,
            job TEXT NOT NULL,
            ilvl INTEGER NOT NULL,
            score INTEGER NOT NULL
        );
        """)

        conn.commit()
    finally:
        cur.close()
        conn.close()


# =========================
# 레이드 / 신청목록 저장
# =========================

def save_active_raids(active_raids: dict):
    conn = get_conn()
    cur = conn.cursor()

    try:
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


# =========================
# 공대 저장 / 조회 / 초기화
# =========================

def clear_saved_parties(raid_name: str):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM raid_party_members WHERE raid_name = %s", (raid_name,))
        cur.execute("DELETE FROM raid_parties WHERE raid_name = %s", (raid_name,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def save_generated_parties(
    raid_name: str,
    raids: list[dict],
    waiting_members: list[dict],
    excluded_members: list[dict] | None = None
):
    if excluded_members is None:
        excluded_members = []

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM raid_party_members WHERE raid_name = %s", (raid_name,))
        cur.execute("DELETE FROM raid_parties WHERE raid_name = %s", (raid_name,))

        for idx, raid in enumerate(raids, start=1):
            cur.execute(
                """
                INSERT INTO raid_parties (raid_name, raid_no)
                VALUES (%s, %s)
                """,
                (raid_name, idx)
            )

            for order_idx, member in enumerate(raid["party1"], start=1):
                cur.execute(
                    """
                    INSERT INTO raid_party_members
                    (raid_name, raid_no, party_name, position_order,
                     user_id, user_name, character_name, job, ilvl, score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        raid_name, idx, "party1", order_idx,
                        member["user_id"], member["user_name"], member["name"],
                        member["job"], member["ilvl"], member["score"]
                    )
                )

            for order_idx, member in enumerate(raid["party2"], start=1):
                cur.execute(
                    """
                    INSERT INTO raid_party_members
                    (raid_name, raid_no, party_name, position_order,
                     user_id, user_name, character_name, job, ilvl, score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        raid_name, idx, "party2", order_idx,
                        member["user_id"], member["user_name"], member["name"],
                        member["job"], member["ilvl"], member["score"]
                    )
                )

        for order_idx, member in enumerate(waiting_members, start=1):
            cur.execute(
                """
                INSERT INTO raid_party_members
                (raid_name, raid_no, party_name, position_order,
                 user_id, user_name, character_name, job, ilvl, score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    raid_name, 0, "waiting", order_idx,
                    member["user_id"], member["user_name"], member["name"],
                    member["job"], member["ilvl"], member["score"]
                )
            )

        for order_idx, member in enumerate(excluded_members, start=1):
            cur.execute(
                """
                INSERT INTO raid_party_members
                (raid_name, raid_no, party_name, position_order,
                 user_id, user_name, character_name, job, ilvl, score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    raid_name, 0, "excluded", order_idx,
                    member["user_id"], member["user_name"], member["name"],
                    member["job"], member["ilvl"], member["score"]
                )
            )

        conn.commit()
    finally:
        cur.close()
        conn.close()


def load_generated_parties(raid_name: str):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT raid_no
            FROM raid_parties
            WHERE raid_name = %s
            ORDER BY raid_no
        """, (raid_name,))
        raid_rows = cur.fetchall()

        if not raid_rows:
            return [], [], []

        raids = []
        for row in raid_rows:
            raids.append({
                "raid_no": row["raid_no"],
                "party1": [],
                "party2": []
            })

        raid_map = {raid["raid_no"]: raid for raid in raids}

        cur.execute("""
            SELECT raid_no, party_name, position_order,
                   user_id, user_name, character_name, job, ilvl, score
            FROM raid_party_members
            WHERE raid_name = %s
            ORDER BY raid_no, party_name, position_order, id
        """, (raid_name,))
        rows = cur.fetchall()

        waiting_members = []
        excluded_members = []

        for row in rows:
            member = {
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "name": row["character_name"],
                "job": row["job"],
                "ilvl": row["ilvl"],
                "score": row["score"],
            }

            if row["party_name"] == "waiting":
                waiting_members.append(member)
                continue

            if row["party_name"] == "excluded":
                excluded_members.append(member)
                continue

            raid_no = row["raid_no"]
            if raid_no not in raid_map:
                continue

            if row["party_name"] == "party1":
                raid_map[raid_no]["party1"].append(member)
            elif row["party_name"] == "party2":
                raid_map[raid_no]["party2"].append(member)

        clean_raids = []
        for raid in raids:
            clean_raids.append({
                "party1": raid["party1"],
                "party2": raid["party2"]
            })

        return clean_raids, waiting_members, excluded_members

    finally:
        cur.close()
        conn.close()

