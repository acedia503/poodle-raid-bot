# party_helpers.py
# 저장된 공대 데이터 조작 유틸

def find_member_in_saved_parties(
    raids: list[dict],
    waiting_members: list[dict],
    excluded_members: list[dict],
    character_name: str
):
    for raid_idx, raid in enumerate(raids):
        for party_name in ("party1", "party2"):
            for member_idx, member in enumerate(raid[party_name]):
                if member["name"] == character_name:
                    return {
                        "location": "raid",
                        "raid_index": raid_idx,
                        "party_name": party_name,
                        "member_index": member_idx,
                        "member": member,
                    }

    for member_idx, member in enumerate(waiting_members):
        if member["name"] == character_name:
            return {
                "location": "waiting",
                "member_index": member_idx,
                "member": member,
            }

    for member_idx, member in enumerate(excluded_members):
        if member["name"] == character_name:
            return {
                "location": "excluded",
                "member_index": member_idx,
                "member": member,
            }

    return None


def remove_member_from_saved_parties(
    raids: list[dict],
    waiting_members: list[dict],
    excluded_members: list[dict],
    found: dict
):
    if found["location"] == "raid":
        return raids[found["raid_index"]][found["party_name"]].pop(found["member_index"])

    if found["location"] == "waiting":
        return waiting_members.pop(found["member_index"])

    if found["location"] == "excluded":
        return excluded_members.pop(found["member_index"])

    return None


def place_member_to_destination(
    raids: list[dict],
    waiting_members: list[dict],
    excluded_members: list[dict],
    member: dict,
    move_type: str,
    target_raid_no: int | None = None,
    target_party_no: int | None = None
):
    if move_type == "waiting":
        waiting_members.append(member)
        return

    if move_type == "excluded":
        excluded_members.append(member)
        return

    if move_type == "raid":
        if target_raid_no is None or target_party_no is None:
            raise ValueError("공대 이동에는 대상공대/대상파티가 필요합니다.")

        target_raid = raids[target_raid_no - 1]
        target_party_name = f"party{target_party_no}"
        target_raid[target_party_name].append(member)
        return

    raise ValueError(f"지원하지 않는 move_type: {move_type}")


def get_party_size(party: list[dict]) -> int:
    return len(party)
