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

def raid_has_same_user(
    raid: dict[str, list[dict[str, Any]]],
    user_id: int,
) -> bool:
    """해당 공대(2개 파티 포함)에 같은 user_id가 이미 있는지 확인"""
    for party_name in ("party1", "party2"):
        for member in raid[party_name]:
            if member.get("user_id") == user_id:
                return True
    return False


def find_placeable_candidate(
    candidates: list[dict[str, Any]],
    raid: dict[str, list[dict[str, Any]]],
    party: list[dict[str, Any]],
    prefer_priority: bool,
):
    """
    후보 중에서
    - 현재 공대에 같은 user_id가 없는 사람만 추리고
    - 그 안에서 가장 적절한 후보를 pick_best_candidate로 선택
    """
    valid_candidates = [
        m for m in candidates
        if not raid_has_same_user(raid, m["user_id"])
    ]

    if not valid_candidates:
        return None

    return pick_best_candidate(
        valid_candidates,
        party,
        prefer_priority=prefer_priority,
    )


def get_available_raids(
    raids: list[dict[str, list[dict[str, Any]]]],
    raid_size: int,
) -> list[dict[str, list[dict[str, Any]]]]:
    """정원이 아직 남아 있는 공대만 반환"""
    return [
        r for r in raids
        if len(r["party1"]) + len(r["party2"]) < raid_size
    ]


def get_possible_parties(
    raid: dict[str, list[dict[str, Any]]],
    party_size: int,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """정원이 남아 있는 파티 목록 반환"""
    possible_parties: list[tuple[str, list[dict[str, Any]]]] = []

    if len(raid["party1"]) < party_size:
        possible_parties.append(("party1", raid["party1"]))
    if len(raid["party2"]) < party_size:
        possible_parties.append(("party2", raid["party2"]))

    return possible_parties


def pick_target_raid(
    available_raids: list[dict[str, list[dict[str, Any]]]],
):
    """
    가장 약한 공대부터 채우기 위해
    총점 -> 총 아이템레벨 -> 현재 인원 수 순으로 낮은 공대 선택
    """
    return min(
        available_raids,
        key=lambda r: (
            raid_score_sum(r),
            raid_ilvl_sum(r),
            len(r["party1"]) + len(r["party2"]),
        ),
    )


def pick_target_party(
    possible_parties: list[tuple[str, list[dict[str, Any]]]],
) -> tuple[str, list[dict[str, Any]]]:
    """점수가 더 낮은 파티부터 채우기"""
    possible_parties.sort(key=lambda x: party_score_sum(x[1]))
    return possible_parties[0]


def build_balanced_raids(refreshed_members: list[dict[str, Any]]):
    raid_size = 8
    party_size = 4

    normalized_members: list[dict[str, Any]] = []
    invalid_members: list[str] = []
    seen_identities: set[tuple[int, str]] = set()

    # 1) 데이터 정규화 + 중복 제거
    for raw in refreshed_members:
        member = normalize_member(raw)
        if member is None:
            invalid_members.append("잘못된 멤버 데이터 1건 제외")
            continue

        identity = member_identity(member)
        if identity in seen_identities:
            invalid_members.append(
                f"중복 데이터 제외: {member['user_name']} | {member['name']}"
            )
            continue

        seen_identities.add(identity)
        normalized_members.append(member)

    # 2) 역할군 분리
    healers, supports, others = split_members_by_job(normalized_members)

    # 3) 생성 가능한 공대 수 계산
    max_by_people = len(normalized_members) // raid_size
    max_by_healers = len(healers)
    raid_count = min(max_by_people, max_by_healers)

    if raid_count == 0:
        reason = "치유성이 부족해서 공대를 만들 수 없습니다."
        if invalid_members:
            return [], [], invalid_members + [reason]
        return [], [], [reason]

    usable_count = raid_count * raid_size

    # 4) 공대 초기화
    raids: list[dict[str, list[dict[str, Any]]]] = [
        {"party1": [], "party2": []}
        for _ in range(raid_count)
    ]

    # 5) 공대당 필수 힐러 1명씩 배치
    mandatory_healers = healers[:raid_count]
    remaining_healers = healers[raid_count:]

    for i, healer in enumerate(mandatory_healers):
        assign_member_to_party(raids[i], "party2", healer)

    # 6) 추가 핵심 인원 선배치
    # 우선순위: 남는 힐러 > 서포트
    for raid in raids:
        candidate = find_placeable_candidate(
            remaining_healers,
            raid,
            raid["party1"],
            prefer_priority=True,
        )
        if candidate is not None:
            assign_member_to_party(raid, "party1", candidate)
            remove_member(remaining_healers, candidate)
            continue

        candidate = find_placeable_candidate(
            supports,
            raid,
            raid["party1"],
            prefer_priority=True,
        )
        if candidate is not None:
            assign_member_to_party(raid, "party1", candidate)
            remove_member(supports, candidate)

    # 7) 남은 인원 풀
    remaining_pool = remaining_healers + supports + others
    remaining_pool.sort(key=member_sort_key, reverse=True)

    already_used = sum(len(r["party1"]) + len(r["party2"]) for r in raids)
    slots_left = max(0, usable_count - already_used)

    assign_members = remaining_pool[:slots_left]
    waiting_members = remaining_pool[slots_left:]
    waiting_members.sort(key=member_sort_key, reverse=True)

    # 8) 남은 슬롯 채우기
    while assign_members:
        available_raids = get_available_raids(raids, raid_size)
        if not available_raids:
            break

        placed = False

        # 가장 약한 공대부터 시도
        sorted_raids = sorted(
            available_raids,
            key=lambda r: (
                raid_score_sum(r),
                raid_ilvl_sum(r),
                len(r["party1"]) + len(r["party2"]),
            ),
        )

        for target_raid in sorted_raids:
            possible_parties = get_possible_parties(target_raid, party_size)
            if not possible_parties:
                continue

            target_party_name, target_party = pick_target_party(possible_parties)

            candidate = find_placeable_candidate(
                assign_members,
                target_raid,
                target_party,
                prefer_priority=False,
            )

            if candidate is None:
                continue

            assign_member_to_party(target_raid, target_party_name, candidate)
            remove_member(assign_members, candidate)
            placed = True
            break

        if not placed:
            # 남은 사람들은 어떤 공대에도 더 이상 못 들어가는 상태
            waiting_members.extend(assign_members)
            waiting_members.sort(key=member_sort_key, reverse=True)
            assign_members.clear()
            break

    return raids, waiting_members, invalid_members


# ----------------------------
# 5. 결과 출력
# ----------------------------

def format_member_line(member: dict[str, Any]) -> str:
    return (
        f"{member.get('user_name', '알수없음')} | "
        f"{member.get('name', '-')} | "
        f"{member.get('job', '-')} | "
        f"템렙 {safe_int(member.get('ilvl'), 0)} | "
        f"아툴 {safe_int(member.get('score'), 0)}"
    )


def format_raid_result(
    레이드이름: str,
    raids: list[dict[str, list[dict[str, Any]]]],
    waiting_members: list[dict[str, Any]],
    invalid_members: list[str]
) -> str:
    result_lines = [f"[{레이드이름}] 공대 생성 결과"]
    raid_scores: list[int] = []
    raid_avg_scores: list[int] = []
    raid_avg_ilvls: list[int] = []

    for idx, raid in enumerate(raids, start=1):
        party1 = raid.get("party1", [])
        party2 = raid.get("party2", [])

        total_members = len(party1) + len(party2)
        total_score = raid_score_sum(raid)
        total_ilvl = raid_ilvl_sum(raid)

        avg_score = total_score // total_members if total_members else 0
        avg_ilvl = total_ilvl // total_members if total_members else 0

        party1_count = len(party1)
        party2_count = len(party2)

        party1_score = party_score_sum(party1)
        party2_score = party_score_sum(party2)

        party1_ilvl = sum(safe_int(m.get("ilvl"), 0) for m in party1)
        party2_ilvl = sum(safe_int(m.get("ilvl"), 0) for m in party2)

        party1_avg_score = party1_score // party1_count if party1_count else 0
        party2_avg_score = party2_score // party2_count if party2_count else 0

        party1_avg_ilvl = party1_ilvl // party1_count if party1_count else 0
        party2_avg_ilvl = party2_ilvl // party2_count if party2_count else 0

        party1_jobs = ", ".join(m.get("job", "-") for m in party1 if m) or "-"
        party2_jobs = ", ".join(m.get("job", "-") for m in party2 if m) or "-"

        raid_scores.append(total_score)
        raid_avg_scores.append(avg_score)
        raid_avg_ilvls.append(avg_ilvl)

        result_lines.append(
            f"\n[{idx}공대] "
            f"총 아툴: {total_score} | 평균 아툴: {avg_score} | 평균 템렙: {avg_ilvl}"
        )

        result_lines.append(
            f"- 1파티 | 총 아툴: {party1_score} | 평균 아툴: {party1_avg_score} | "
            f"평균 템렙: {party1_avg_ilvl} | 직업: {party1_jobs}"
        )
        for member in party1:
            result_lines.append(f"  · {format_member_line(member)}")

        result_lines.append(
            f"- 2파티 | 총 아툴: {party2_score} | 평균 아툴: {party2_avg_score} | "
            f"평균 템렙: {party2_avg_ilvl} | 직업: {party2_jobs}"
        )
        for member in party2:
            result_lines.append(f"  · {format_member_line(member)}")

        result_lines.append(
            "- 균형요약 | "
            f"파티 총 아툴 차이: {abs(party1_score - party2_score)} | "
            f"파티 평균 아툴 차이: {abs(party1_avg_score - party2_avg_score)} | "
            f"파티 평균 템렙 차이: {abs(party1_avg_ilvl - party2_avg_ilvl)}"
        )

    if waiting_members:
        waiting_count = len(waiting_members)
        waiting_score = sum(safe_int(m.get("score"), 0) for m in waiting_members)
        waiting_ilvl = sum(safe_int(m.get("ilvl"), 0) for m in waiting_members)
        waiting_avg_score = waiting_score // waiting_count if waiting_count else 0
        waiting_avg_ilvl = waiting_ilvl // waiting_count if waiting_count else 0

        result_lines.append(
            f"\n[대기 인원] 총 아툴: {waiting_score} | "
            f"평균 아툴: {waiting_avg_score} | 평균 템렙: {waiting_avg_ilvl}"
        )
        for member in waiting_members:
            result_lines.append(format_member_line(member))

    if invalid_members:
        result_lines.append("\n[제외 인원]")
        result_lines.extend(invalid_members)

    if raid_scores:
        result_lines.append("\n[균형 요약]")
        result_lines.append(f"최고 공대 총 아툴: {max(raid_scores)}")
        result_lines.append(f"최저 공대 총 아툴: {min(raid_scores)}")
        result_lines.append(f"공대 총 아툴 차이: {max(raid_scores) - min(raid_scores)}")
        result_lines.append(f"최고 공대 평균 아툴: {max(raid_avg_scores)}")
        result_lines.append(f"최저 공대 평균 아툴: {min(raid_avg_scores)}")
        result_lines.append(f"공대 평균 아툴 차이: {max(raid_avg_scores) - min(raid_avg_scores)}")

    return "\n".join(result_lines)
