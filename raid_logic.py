# raid_logic.py
# 공대 자동 생성 알고리즘 담당

from __future__ import annotations

from typing import Any

from models import JOB_POLICY


DEFAULT_JOB_POLICY = {
    "role": "unknown",
    "party2_required": False,
    "party1_priority": 99,
}


# ----------------------------
# 0. 안전 보조 함수
# ----------------------------

def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_member(member: dict[str, Any]) -> dict[str, Any] | None:
    """
    외부/API/저장소에서 온 member dict를 안전하게 정규화.
    필수값이 없으면 None 반환.
    """
    if not isinstance(member, dict):
        return None

    user_id = safe_int(member.get("user_id"), 0)
    user_name = str(member.get("user_name", "알수없음")).strip() or "알수없음"
    name = str(member.get("name", "")).strip()
    job = str(member.get("job", "")).strip()
    ilvl = safe_int(member.get("ilvl"), 0)
    score = safe_int(member.get("score"), 0)

    if user_id <= 0:
        return None
    if not name:
        return None
    if not job:
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


def member_identity(member: dict[str, Any]) -> tuple[int, str]:
    return (
        safe_int(member.get("user_id"), 0),
        str(member.get("name", "")).strip(),
    )


def member_sort_key(member: dict[str, Any]) -> tuple[int, int]:
    return (
        safe_int(member.get("score"), 0),
        safe_int(member.get("ilvl"), 0),
    )


# ----------------------------
# 1. 직업 관련 함수
# ----------------------------

def get_job_policy(job: str) -> dict[str, Any]:
    if not isinstance(job, str):
        return DEFAULT_JOB_POLICY
    return JOB_POLICY.get(job, DEFAULT_JOB_POLICY)


def is_healer(job: str) -> bool:
    return get_job_policy(job).get("role") == "healer"


def is_support(job: str) -> bool:
    return get_job_policy(job).get("role") == "support"


# ----------------------------
# 2. 계산 함수
# ----------------------------

def party_jobs(party: list[dict[str, Any]]) -> set[str]:
    jobs = set()
    for m in party:
        if not m:
            continue
        job = str(m.get("job", "")).strip()
        if job:
            jobs.add(job)
    return jobs


def party_score_sum(party: list[dict[str, Any]]) -> int:
    return sum(safe_int(m.get("score"), 0) for m in party if m)


def raid_score_sum(raid: dict[str, list[dict[str, Any]]]) -> int:
    return party_score_sum(raid.get("party1", [])) + party_score_sum(raid.get("party2", []))


def raid_ilvl_sum(raid: dict[str, list[dict[str, Any]]]) -> int:
    members = raid.get("party1", []) + raid.get("party2", [])
    return sum(safe_int(m.get("ilvl"), 0) for m in members if m)


def remove_member(pool: list[dict[str, Any]], member: dict[str, Any] | None) -> None:
    if member is None:
        return

    target_id = member_identity(member)

    for i, m in enumerate(pool):
        if member_identity(m) == target_id:
            pool.pop(i)
            return


# ----------------------------
# 3. 후보 선택 함수
# ----------------------------

def pick_best_candidate(
    candidates: list[dict[str, Any]],
    party: list[dict[str, Any]],
    prefer_priority: bool = False
) -> dict[str, Any] | None:
    if not candidates:
        return None

    existing_jobs = party_jobs(party)

    def candidate_key(member: dict[str, Any]):
        job = str(member.get("job", "")).strip()
        policy = get_job_policy(job)
        duplicate_penalty = 0 if job not in existing_jobs else 1

        if prefer_priority:
            return (
                duplicate_penalty,
                safe_int(policy.get("party1_priority"), 99),
                -safe_int(member.get("score"), 0),
                -safe_int(member.get("ilvl"), 0),
            )

        return (
            duplicate_penalty,
            -safe_int(member.get("score"), 0),
            -safe_int(member.get("ilvl"), 0),
        )

    return min(candidates, key=candidate_key)


def split_members_by_job(members: list[dict[str, Any]]):
    healers: list[dict[str, Any]] = []
    supports: list[dict[str, Any]] = []
    others: list[dict[str, Any]] = []

    for m in members:
        if is_healer(str(m.get("job", ""))):
            healers.append(m)
        elif is_support(str(m.get("job", ""))):
            supports.append(m)
        else:
            others.append(m)

    healers.sort(key=member_sort_key, reverse=True)
    supports.sort(key=member_sort_key, reverse=True)
    others.sort(key=member_sort_key, reverse=True)

    return healers, supports, others


def assign_member_to_party(raid: dict[str, list[dict[str, Any]]], party_name: str, member: dict[str, Any] | None):
    if member is None:
        return
    if party_name not in ("party1", "party2"):
        raise ValueError(f"유효하지 않은 파티 이름입니다: {party_name}")
    raid[party_name].append(member)


# ----------------------------
# 4. 공대 생성 알고리즘
# ----------------------------

def build_balanced_raids(refreshed_members: list[dict[str, Any]]):
    raid_size = 8
    party_size = 4

    normalized_members: list[dict[str, Any]] = []
    invalid_members: list[str] = []
    seen_identities: set[tuple[int, str]] = set()

    for raw in refreshed_members:
        member = normalize_member(raw)
        if member is None:
            invalid_members.append(f"잘못된 데이터 제외: {raw!r}")
            continue

        identity = member_identity(member)
        if identity in seen_identities:
            invalid_members.append(
                f"중복 데이터 제외: {member['user_name']} | {member['name']}"
            )
            continue

        seen_identities.add(identity)
        normalized_members.append(member)

    healers, supports, others = split_members_by_job(normalized_members)

    max_by_people = len(normalized_members) // raid_size
    max_by_healers = len(healers)
    raid_count = min(max_by_people, max_by_healers)

    if raid_count == 0:
        reason = "치유성이 부족해서 공대를 만들 수 없습니다."
        if invalid_members:
            return [], [], invalid_members + [reason]
        return [], [], [reason]

    usable_count = raid_count * raid_size

    raids: list[dict[str, list[dict[str, Any]]]] = []
    for _ in range(raid_count):
        raids.append({
            "party1": [],
            "party2": [],
        })

    mandatory_healers = healers[:raid_count]
    remaining_healers = healers[raid_count:]

    for i, healer in enumerate(mandatory_healers):
        assign_member_to_party(raids[i], "party2", healer)

    for raid in raids:
        candidate = None

        if remaining_healers:
            candidate = pick_best_candidate(
                remaining_healers, raid["party1"], prefer_priority=True
            )
            remove_member(remaining_healers, candidate)
            assign_member_to_party(raid, "party1", candidate)

        elif supports:
            candidate = pick_best_candidate(
                supports, raid["party1"], prefer_priority=True
            )
            remove_member(supports, candidate)
            assign_member_to_party(raid, "party1", candidate)

    remaining_pool = remaining_healers + supports + others
    remaining_pool.sort(key=member_sort_key, reverse=True)

    already_used = sum(len(r["party1"]) + len(r["party2"]) for r in raids)
    slots_left = max(0, usable_count - already_used)

    assign_members = remaining_pool[:slots_left]
    waiting_members = remaining_pool[slots_left:]
    waiting_members.sort(key=member_sort_key, reverse=True)

    while assign_members:
        available_raids = [
            r for r in raids if len(r["party1"]) + len(r["party2"]) < raid_size
        ]

        if not available_raids:
            break

        target_raid = min(
            available_raids,
            key=lambda r: (
                raid_score_sum(r),
                raid_ilvl_sum(r),
                len(r["party1"]) + len(r["party2"]),
            )
        )

        possible_parties = []
        if len(target_raid["party1"]) < party_size:
            possible_parties.append(("party1", target_raid["party1"]))
        if len(target_raid["party2"]) < party_size:
            possible_parties.append(("party2", target_raid["party2"]))

        if not possible_parties:
            break

        possible_parties.sort(key=lambda x: party_score_sum(x[1]))
        target_party_name, target_party = possible_parties[0]

        candidate = pick_best_candidate(assign_members, target_party, prefer_priority=False)
        if candidate is None:
            break

        assign_member_to_party(target_raid, target_party_name, candidate)
        remove_member(assign_members, candidate)

    return raids, waiting_members, invalid_members


# ----------------------------
# 5. 결과 출력
# ----------------------------

def format_member_line(member: dict[str, Any]) -> str:
    return (
        f"{member.get('user_name', '알수없음')} | "
        f"{member.get('name', '-') } | "
        f"{member.get('job', '-') } | "
        f"{safe_int(member.get('ilvl'), 0)} | "
        f"{safe_int(member.get('score'), 0)}"
    )


def format_raid_result(
    레이드이름: str,
    raids: list[dict[str, list[dict[str, Any]]]],
    waiting_members: list[dict[str, Any]],
    invalid_members: list[str]
) -> str:
    result_lines = [f"[{레이드이름}] 공대 생성 결과"]
    raid_scores = []

    for idx, raid in enumerate(raids, start=1):
        party1 = raid.get("party1", [])
        party2 = raid.get("party2", [])

        total_members = len(party1) + len(party2)
        total_score = raid_score_sum(raid)
        total_ilvl = raid_ilvl_sum(raid)

        avg_score = total_score // total_members if total_members else 0
        avg_ilvl = total_ilvl // total_members if total_members else 0

        party1_score = party_score_sum(party1)
        party2_score = party_score_sum(party2)

        party1_jobs = ", ".join(m.get("job", "-") for m in party1 if m) or "-"
        party2_jobs = ", ".join(m.get("job", "-") for m in party2 if m) or "-"

        raid_scores.append(total_score)

        result_lines.append(
            f"\n{idx}공대 | 총 아툴: {total_score} | 평균 아툴: {avg_score} | 평균 템렙: {avg_ilvl}"
        )

        result_lines.append(f"- 1파티 | 합계 아툴: {party1_score} | 직업: {party1_jobs}")
        for member in party1:
            result_lines.append(format_member_line(member))

        result_lines.append(f"- 2파티 | 합계 아툴: {party2_score} | 직업: {party2_jobs}")
        for member in party2:
            result_lines.append(format_member_line(member))

    if waiting_members:
        result_lines.append("\n[대기 인원]")
        for member in waiting_members:
            result_lines.append(format_member_line(member))

    if invalid_members:
        result_lines.append("\n[제외 인원]")
        result_lines.extend(invalid_members)

    if raid_scores:
        result_lines.append("\n[균형 요약]")
        result_lines.append(f"최고 공대 총 아툴: {max(raid_scores)}")
        result_lines.append(f"최저 공대 총 아툴: {min(raid_scores)}")
        result_lines.append(f"차이: {max(raid_scores) - min(raid_scores)}")

    return "\n".join(result_lines)
