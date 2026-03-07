# storage.py
# PostgreSQL 저장 담당 (레이드 + 신청목록 + 공대결과)

from __future__ import annotations

import os
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from models import Character


VALID_PARTY_NAMES = {"party1", "party2", "waiting", "excluded"}


# =========================
# 공통 유틸
# =========================

def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return database_url


def get_conn():
    return psycopg2.connect(get_database_url(), sslmode="require")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def normalize_member(member: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(member, dict):
        return None

    user_id = safe_int(member.get("user_id"), 0)
    user_name = normalize_text(member.get("user_name"), "알수없음")
    name = normalize_text(member.get("name"))
    job = normalize_text(member.get("job"))
    ilvl = safe_int(member.get("ilvl"), 0)
    score = safe_int(member.get("score"), 0)

    if user_id <= 0 or not name or not job:
        return None

    if ilvl < 0:
        ilvl = 0
    if score < 0:
        score = 0

    return {
        "user_id": user_id,
        "user_name": user_name,
        "name": name,
        "job": job,
        "ilvl": ilvl,
        "score": score,
    }


def normalize_character(character: Character) -> Character:
    return Character(
        user_id=safe_int(character.user_id, 0),
        user_name=normalize_text(character.user_name, "알수없음"),
        name=normalize_text(character.name),
    )


# =========================
# DB 초기화
# =========================

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS raids (
                raid_name TEXT PRIMARY KEY,
                min_ilvl INTEGER NOT NULL CHECK (min_ilvl >= 0)
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS raid_members (
                id SERIAL PRIMARY KEY,
                raid_name TEXT NOT NULL REFERENCES raids(raid_name) ON DELETE CASCADE,
                user_id BIGINT NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                UNIQUE (raid_name, user_id, character_name)
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS raid_parties (
                id SERIAL PRIMARY KEY,
                raid_name TEXT NOT NULL REFERENCES raids(raid_name) ON DELETE CASCADE,
                raid_no INTEGER NOT NULL CHECK (raid_no > 0),
                UNIQUE (raid_name, raid_no)
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS raid_party_members (
                id SERIAL PRIMARY KEY,
                raid_name TEXT NOT NULL REFERENCES raids(raid_name) ON DELETE CASCADE,
                raid_no INTEGER NOT NULL CHECK (raid_no >= 0),
                party_name TEXT NOT NULL CHECK (
                    party_name IN ('party1', 'party2', 'waiting', 'excluded')
                ),
                position_order INTEGER NOT NULL CHECK (position_order > 0),
                user_id BIGINT NOT NULL,
                user_name TEXT NOT NULL,
                character_name TEXT NOT NULL,
                job TEXT NOT NULL,
                ilvl INTEGER NOT NULL CHECK (ilvl >= 0),
                score INTEGER NOT NULL CHECK (score >= 0)
            );
            """)

            cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_raid_party_position
            ON raid_party_members (raid_name, raid_no, party_name, position_order);
            """)

            cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_raid_party_member
            ON raid_party_members (raid_name, raid_no, party_name, user_id, character_name);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_members_raid_name
            ON raid_members (raid_name);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raid_party_members_raid_name
            ON raid_party_members (raid_name);
            """)


# =========================
# 레이드 기본 정보
# =========================

def save_raid(raid_name: str, min_ilvl: int) -> None:
    safe_raid_name = normalize_text(raid_name)
    if not safe_raid_name:
        raise ValueError("raid_name이 비어 있습니다.")

    safe_min_ilvl = max(0, safe_int(min_ilvl, 0))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raids (raid_name, min_ilvl)
                VALUES (%s, %s)
                ON CONFLICT (raid_name)
                DO UPDATE SET min_ilvl = EXCLUDED.min_ilvl
                """,
                (safe_raid_name, safe_min_ilvl)
            )


def load_active_raids() -> dict[str, dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            active_raids: dict[str, dict[str, Any]] = {}

            cur.execute("""
                SELECT raid_name, min_ilvl
                FROM raids
                ORDER BY raid_name
            """)
            raid_rows = cur.fetchall()

            for row in raid_rows:
                active_raids[row["raid_name"]] = {
                    "min_ilvl": safe_int(row["min_ilvl"], 0),
                    "members": []
                }

            cur.execute("""
                SELECT raid_name, user_id, user_name, character_name
                FROM raid_members
                ORDER BY raid_name, id
            """)
            member_rows = cur.fetchall()

            for row in member_rows:
                raid_name = row["raid_name"]
                if raid_name not in active_raids:
                    continue

                try:
                    active_raids[raid_name]["members"].append(
                        Character(
                            user_id=safe_int(row["user_id"], 0),
                            user_name=normalize_text(row["user_name"], "알수없음"),
                            name=normalize_text(row["character_name"]),
                        )
                    )
                except (TypeError, ValueError):
                    continue

            return active_raids


def load_raid(raid_name: str) -> dict[str, Any] | None:
    safe_raid_name = normalize_text(raid_name)
    if not safe_raid_name:
        return None

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT raid_name, min_ilvl
                FROM raids
                WHERE raid_name = %s
            """, (safe_raid_name,))
            row = cur.fetchone()

            if not row:
                return None

            raid_data = {
                "min_ilvl": safe_int(row["min_ilvl"], 0),
                "members": []
            }

            cur.execute("""
                SELECT user_id, user_name, character_name
                FROM raid_members
                WHERE raid_name = %s
                ORDER BY id
            """, (safe_raid_name,))
            members = cur.fetchall()

            for m in members:
                try:
                    raid_data["members"].append(
                        Character(
                            user_id=safe_int(m["user_id"], 0),
                            user_name=normalize_text(m["user_name"], "알수없음"),
                            name=normalize_text(m["character_name"]),
                        )
                    )
                except (TypeError, ValueError):
                    continue

            return raid_data


def delete_raid(raid_name: str) -> bool:
    safe_raid_name = normalize_text(raid_name)
    if not safe_raid_name:
        return False

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM raids WHERE raid_name = %s",
                (safe_raid_name,)
            )
            return cur.rowcount > 0


def count_raid_members(raid_name: str) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM raid_members
                WHERE raid_name = %s
                """,
                (raid_name,)
            )
            row = cur.fetchone()
            return row[0] if row else 0

# =========================
# 신청자 저장
# =========================

def save_raid_members(raid_name: str, members: list[Character]) -> None:
    """
    특정 레이드의 신청자 목록만 교체 저장.
    다른 레이드 데이터는 건드리지 않음.
    """
    safe_raid_name = normalize_text(raid_name)
    if not safe_raid_name:
        raise ValueError("raid_name이 비어 있습니다.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM raids WHERE raid_name = %s", (safe_raid_name,))
            if cur.fetchone() is None:
                raise ValueError(f"존재하지 않는 레이드입니다: {safe_raid_name}")

            cur.execute(
                "DELETE FROM raid_members WHERE raid_name = %s",
                (safe_raid_name,)
            )

            seen_members: set[tuple[int, str]] = set()

            for raw_member in members:
                if not isinstance(raw_member, Character):
                    continue

                try:
                    member = normalize_character(raw_member)
                except (TypeError, ValueError):
                    continue

                if member.user_id <= 0 or not member.name:
                    continue

                identity = (member.user_id, member.name)
                if identity in seen_members:
                    continue
                seen_members.add(identity)

                cur.execute(
                    """
                    INSERT INTO raid_members
                    (raid_name, user_id, user_name, character_name)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        safe_raid_name,
                        member.user_id,
                        member.user_name,
                        member.name,
                    )
                )


def add_raid_member(raid_name: str, member: Character) -> bool:
    safe_raid_name = normalize_text(raid_name)
    if not safe_raid_name:
        raise ValueError("raid_name이 비어 있습니다.")

    member = normalize_character(member)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM raids WHERE raid_name = %s", (safe_raid_name,))
            if cur.fetchone() is None:
                raise ValueError(f"존재하지 않는 레이드입니다: {safe_raid_name}")

            cur.execute(
                """
                INSERT INTO raid_members
                (raid_name, user_id, user_name, character_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (raid_name, user_id, character_name) DO NOTHING
                """,
                (
                    safe_raid_name,
                    member.user_id,
                    member.user_name,
                    member.name,
                )
            )
            return cur.rowcount > 0


def remove_raid_member(raid_name: str, user_id: int, character_name: str) -> bool:
    safe_raid_name = normalize_text(raid_name)
    safe_character_name = normalize_text(character_name)

    if not safe_raid_name or not safe_character_name:
        return False

    safe_user_id = safe_int(user_id, 0)
    if safe_user_id <= 0:
        return False

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM raid_members
                WHERE raid_name = %s
                  AND user_id = %s
                  AND character_name = %s
                """,
                (safe_raid_name, safe_user_id, safe_character_name)
            )
            return cur.rowcount > 0


# =========================
# 공대 저장 / 조회 / 초기화
# =========================

def clear_saved_parties(raid_name: str) -> None:
    safe_raid_name = normalize_text(raid_name)
    if not safe_raid_name:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM raid_party_members WHERE raid_name = %s",
                (safe_raid_name,)
            )
            cur.execute(
                "DELETE FROM raid_parties WHERE raid_name = %s",
                (safe_raid_name,)
            )


def save_generated_parties(
    raid_name: str,
    raids: list[dict[str, Any]],
    waiting_members: list[dict[str, Any]],
    excluded_members: list[dict[str, Any]] | None = None,
) -> None:
    """
    특정 레이드의 공대 결과만 교체 저장.
    다른 레이드 결과는 건드리지 않음.
    """
    if excluded_members is None:
        excluded_members = []

    safe_raid_name = normalize_text(raid_name)
    if not safe_raid_name:
        raise ValueError("raid_name이 비어 있습니다.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM raids WHERE raid_name = %s", (safe_raid_name,))
            if cur.fetchone() is None:
                raise ValueError(f"존재하지 않는 레이드입니다: {safe_raid_name}")

            # 위험한 전체 삭제 대신, 해당 레이드의 공대 결과만 삭제
            cur.execute(
                "DELETE FROM raid_party_members WHERE raid_name = %s",
                (safe_raid_name,)
            )
            cur.execute(
                "DELETE FROM raid_parties WHERE raid_name = %s",
                (safe_raid_name,)
            )

            for idx, raid in enumerate(raids, start=1):
                cur.execute(
                    """
                    INSERT INTO raid_parties (raid_name, raid_no)
                    VALUES (%s, %s)
                    """,
                    (safe_raid_name, idx)
                )

                for party_name in ("party1", "party2"):
                    party_members = raid.get(party_name, [])
                    seen_party_members: set[tuple[int, str]] = set()

                    for order_idx, raw_member in enumerate(party_members, start=1):
                        member = normalize_member(raw_member)
                        if member is None:
                            continue

                        identity = (member["user_id"], member["name"])
                        if identity in seen_party_members:
                            continue
                        seen_party_members.add(identity)

                        cur.execute(
                            """
                            INSERT INTO raid_party_members
                            (raid_name, raid_no, party_name, position_order,
                             user_id, user_name, character_name, job, ilvl, score)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                safe_raid_name,
                                idx,
                                party_name,
                                order_idx,
                                member["user_id"],
                                member["user_name"],
                                member["name"],
                                member["job"],
                                member["ilvl"],
                                member["score"],
                            )
                        )

            for party_name, members in (("waiting", waiting_members), ("excluded", excluded_members)):
                seen_special_members: set[tuple[int, str]] = set()

                for order_idx, raw_member in enumerate(members, start=1):
                    member = normalize_member(raw_member)
                    if member is None:
                        continue

                    identity = (member["user_id"], member["name"])
                    if identity in seen_special_members:
                        continue
                    seen_special_members.add(identity)

                    cur.execute(
                        """
                        INSERT INTO raid_party_members
                        (raid_name, raid_no, party_name, position_order,
                         user_id, user_name, character_name, job, ilvl, score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            safe_raid_name,
                            0,
                            party_name,
                            order_idx,
                            member["user_id"],
                            member["user_name"],
                            member["name"],
                            member["job"],
                            member["ilvl"],
                            member["score"],
                        )
                    )


def load_generated_parties(raid_name: str):
    safe_raid_name = normalize_text(raid_name)
    if not safe_raid_name:
        return [], [], []

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT raid_no
                FROM raid_parties
                WHERE raid_name = %s
                ORDER BY raid_no
            """, (safe_raid_name,))
            raid_rows = cur.fetchall()

            if not raid_rows:
                return [], [], []

            raids = []
            for row in raid_rows:
                raids.append({
                    "raid_no": row["raid_no"],
                    "party1": [],
                    "party2": [],
                })

            raid_map = {raid["raid_no"]: raid for raid in raids}

            cur.execute("""
                SELECT raid_no, party_name, position_order,
                       user_id, user_name, character_name, job, ilvl, score
                FROM raid_party_members
                WHERE raid_name = %s
                ORDER BY raid_no, party_name, position_order, id
            """, (safe_raid_name,))
            rows = cur.fetchall()

            waiting_members = []
            excluded_members = []

            for row in rows:
                member = normalize_member({
                    "user_id": row["user_id"],
                    "user_name": row["user_name"],
                    "name": row["character_name"],
                    "job": row["job"],
                    "ilvl": row["ilvl"],
                    "score": row["score"],
                })
                if member is None:
                    continue

                party_name = row["party_name"]

                if party_name == "waiting":
                    waiting_members.append(member)
                    continue

                if party_name == "excluded":
                    excluded_members.append(member)
                    continue

                raid_no = safe_int(row["raid_no"], 0)
                if raid_no not in raid_map:
                    continue

                if party_name in ("party1", "party2"):
                    raid_map[raid_no][party_name].append(member)

            clean_raids = []
            for raid in raids:
                clean_raids.append({
                    "party1": raid["party1"],
                    "party2": raid["party2"],
                })

            return clean_raids, waiting_members, excluded_members
        



