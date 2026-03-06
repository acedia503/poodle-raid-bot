# raid_logic.py
# 공대 자동 생성 알고리즘 담당

from models import JOB_POLICY


# ----------------------------
# 1. 직업 관련 함수
# ----------------------------

def get_job_policy(job: str) -> dict:
    return JOB_POLICY.get(job, {
        "role": "unknown",
        "party2_required": False,
        "party1_priority": 99
    })


def is_healer(job: str) -> bool:
    return get_job_policy(job)["role"] == "healer"


def is_support(job: str) -> bool:
    return get_job_policy(job)["role"] == "support"


# ----------------------------
# 2. 계산 함수
# ----------------------------

def party_jobs(party: list[dict]) -> set[str]:
    return {m["job"] for m in party if m is not None}


def party_score_sum(party: list[dict]) -> int:
    return sum(m["score"] for m in party if m is not None)


def raid_score_sum(raid: dict) -> int:
    return party_score_sum(raid["party1"]) + party_score_sum(raid["party2"])


def raid_ilvl_sum(raid: dict) -> int:
    return sum(m["ilvl"] for m in raid["party1"] + raid["party2"] if m is not None)


def remove_member(pool: list[dict], member: dict):
    if member is None:
        return

    for i, m in enumerate(pool):
        if m["user_id"] == member["user_id"] and m["name"] == member["name"]:
            pool.pop(i)
            return


# ----------------------------
# 3. 후보 선택 함수
# ----------------------------

def pick_best_candidate(candidates: list[dict], party: list[dict], prefer_priority: bool = False):
    if not candidates:
        return None

    existing_jobs = party_jobs(party)

    def candidate_key(member: dict):
        policy = get_job_policy(member["job"])
        duplicate_penalty = 0 if member["job"] not in existing_jobs else 1

        if prefer_priority:
            return (
                duplicate_penalty,
                policy["party1_priority"],
                -member["score"],
                -member["ilvl"]
            )

        return (
            duplicate_penalty,
            -member["score"],
            -member["ilvl"]
        )

    return sorted(candidates, key=candidate_key)[0]


def split_members_by_job(members: list[dict]):
    healers = []
    supports = []
    others = []

    for m in members:
        if is_healer(m["job"]):
            healers.append(m)
        elif is_support(m["job"]):
            supports.append(m)
        else:
            others.append(m)

    healers.sort(key=lambda x: (x["score"], x["ilvl"]), reverse=True)
    supports.sort(key=lambda x: (x["score"], x["ilvl"]), reverse=True)
    others.sort(key=lambda x: (x["score"], x["ilvl"]), reverse=True)

    return healers, supports, others


def assign_member_to_party(raid: dict, party_name: str, member: dict):
    if member is None:
        return
    raid[party_name].append(member)


# ----------------------------
# 4. 공대 생성 알고리즘
# ----------------------------

def build_balanced_raids(refreshed_members: list[dict]):
    raid_size = 8
    party_size = 4

    healers, supports, others = split_members_by_job(refreshed_members)

    max_by_people = len(refreshed_members) // raid_size
    max_by_healers = len(healers)
    raid_count = min(max_by_people, max_by_healers)

    if raid_count == 0:
        return [], [], "치유성이 부족해서 공대를 만들 수 없습니다."

    usable_count = raid_count * raid_size

    raids = []
    for _ in range(raid_count):
        raids.append({
            "party1": [],
            "party2": []
        })

    mandatory_healers = healers[:raid_count]
    remaining_healers = healers[raid_count:]

    for i, healer in enumerate(mandatory_healers):
        assign_member_to_party(raids[i], "party2", healer)

    for raid in raids:
        candidate = None

        if remaining_healers:
            candidate = pick_best_candidate(remaining_healers, raid["party1"], prefer_priority=True)
            remove_member(remaining_healers, candidate)
            assign_member_to_party(raid, "party1", candidate)

        elif supports:
            candidate = pick_best_candidate(supports, raid["party1"], prefer_priority=True)
            remove_member(supports, candidate)
            assign_member_to_party(raid, "party1", candidate)

    remaining_pool = remaining_healers + supports + others
    remaining_pool.sort(key=lambda x: (x["score"], x["ilvl"]), reverse=True)

    already_used = sum(len(r["party1"]) + len(r["party2"]) for r in raids)
    slots_left = usable_count - already_used

    assign_members = remaining_pool[:slots_left]
    waiting_members = remaining_pool[slots_left:]
    waiting_members.sort(key=lambda x: (x["score"], x["ilvl"]), reverse=True)

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
                len(r["party1"]) + len(r["party2"])
            )
        )

        possible_parties = []
        if len(target_raid["party1"]) < party_size:
            possible_parties.append(("party1", target_raid["party1"]))
        if len(target_raid["party2"]) < party_size:
            possible_parties.append(("party2", target_raid["party2"]))

        possible_parties.sort(key=lambda x: party_score_sum(x[1]))
        target_party_name, target_party = possible_parties[0]

        candidate = pick_best_candidate(assign_members, target_party, prefer_priority=False)
        if candidate is None:
            break

        assign_member_to_party(target_raid, target_party_name, candidate)
        remove_member(assign_members, candidate)

    return raids, waiting_members, None


# ----------------------------
# 5. 결과 출력
# ----------------------------

def format_raid_result(
    레이드이름: str,
    raids: list[dict],
    waiting_members: list[dict],
    invalid_members: list[str]
) -> str:
    result_lines = [f"[{레이드이름}] 공대 생성 결과"]
    raid_scores = []

    for idx, raid in enumerate(raids, start=1):
        total_members = len(raid["party1"]) + len(raid["party2"])
        total_score = raid_score_sum(raid)
        total_ilvl = raid_ilvl_sum(raid)

        avg_score = total_score // total_members if total_members else 0
        avg_ilvl = total_ilvl // total_members if total_members else 0

        party1_score = party_score_sum(raid["party1"])
        party2_score = party_score_sum(raid["party2"])

        party1_jobs = ", ".join([m["job"] for m in raid["party1"] if m is not None]) or "-"
        party2_jobs = ", ".join([m["job"] for m in raid["party2"] if m is not None]) or "-"

        raid_scores.append(total_score)

        result_lines.append(
            f"\n{idx}공대 | 총 아툴: {total_score} | 평균 아툴: {avg_score} | 평균 템렙: {avg_ilvl}"
        )

        result_lines.append(f"- 1파티 | 합계 아툴: {party1_score} | 직업: {party1_jobs}")
        for member in raid["party1"]:
            result_lines.append(
                f"{member['user_name']} | {member['name']} | {member['job']} | {member['ilvl']} | {member['score']}"
            )

        result_lines.append(f"- 2파티 | 합계 아툴: {party2_score} | 직업: {party2_jobs}")
        for member in raid["party2"]:
            result_lines.append(
                f"{member['user_name']} | {member['name']} | {member['job']} | {member['ilvl']} | {member['score']}"
            )

    if waiting_members:
        result_lines.append("\n[대기 인원]")
        for member in waiting_members:
            result_lines.append(
                f"{member['user_name']} | {member['name']} | {member['job']} | {member['ilvl']} | {member['score']}"
            )

    if invalid_members:
        result_lines.append("\n[제외 인원]")
        result_lines.extend(invalid_members)

    if raid_scores:
        result_lines.append("\n[균형 요약]")
        result_lines.append(f"최고 공대 총 아툴: {max(raid_scores)}")
        result_lines.append(f"최저 공대 총 아툴: {min(raid_scores)}")
        result_lines.append(f"차이: {max(raid_scores) - min(raid_scores)}")

    return "\n".join(result_lines)