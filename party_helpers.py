# party_helpers.py
# 저장된 공대 데이터 조작 유틸

from __future__ import annotations


def find_member_in_saved_parties(
    raids: list[dict],
    waiting_members: list[dict],
    excluded_members: list[dict],
    character_name: str,
):
    for raid_idx, raid in enumerate(raids):
        for party_name in ("party1", "party2"):
            party = raid.get(party_name, [])
            for member_idx, member in enumerate(party):
                if member.get("name") == character_name:
                    return {
                        "location": "raid",
                        "raid_index": raid_idx,
                        "party_name": party_name,
                        "member_index": member_idx,
                        "member": member,
                    }

    for member_idx, member in enumerate(waiting_members):
        if member.get("name") == character_name:
            return {
                "location": "waiting",
                "member_index": member_idx,
                "member": member,
            }

    for member_idx, member in enumerate(excluded_members):
        if member.get("name") == character_name:
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
    found: dict,
):
    if not found:
        return None

    location = found.get("location")

    if location == "raid":
        raid_index = found.get("raid_index")
        party_name = found.get("party_name")
        member_index = found.get("member_index")

        if raid_index is None or party_name not in ("party1", "party2") or member_index is None:
            return None

        return raids[raid_index][party_name].pop(member_index)

    if location == "waiting":
        member_index = found.get("member_index")
        if member_index is None:
            return None
        return waiting_members.pop(member_index)

    if location == "excluded":
        member_index = found.get("member_index")
        if member_index is None:
            return None
        return excluded_members.pop(member_index)

    return None


def place_member_to_destination(
    raids: list[dict],
    waiting_members: list[dict],
    excluded_members: list[dict],
    member: dict,
    move_type: str,
    target_raid_no: int | None = None,
    target_party_no: int | None = None,
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

        if target_raid_no < 1 or target_raid_no > len(raids):
            raise ValueError("유효하지 않은 대상 공대 번호입니다.")

        if target_party_no not in (1, 2):
            raise ValueError("대상 파티 번호는 1 또는 2여야 합니다.")

        target_raid = raids[target_raid_no - 1]
        target_party_name = f"party{target_party_no}"
        target_party = target_raid[target_party_name]

        if len(target_party) >= 4:
            raise ValueError("대상 파티가 이미 가득 찼습니다.")

        target_party.append(member)
        return

    raise ValueError(f"지원하지 않는 move_type: {move_type}")


def get_party_size(party: list[dict]) -> int:
    return len(party)


def is_party_full(party: list[dict], max_size: int = 4) -> bool:
    return len(party) >= max_size
