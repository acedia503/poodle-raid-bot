# party_helpers.py
# 저장된 공대 데이터 조작 유틸

from __future__ import annotations

from typing import Any


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def member_identity(member: dict[str, Any]) -> tuple[int, str]:
    return (
        _safe_int(member.get("user_id"), 0),
        _safe_str(member.get("name")),
    )


def is_same_member(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return member_identity(a) == member_identity(b)


def find_member_in_saved_parties(
    raids: list[dict],
    waiting_members: list[dict],
    excluded_members: list[dict],
    target: dict[str, Any],
):
    """
    target dict의 user_id + name 기준으로 저장된 위치를 찾는다.
    반환 예시:
    {
        "location": "raid",
        "raid_index": 0,
        "party_name": "party1",
        "member_index": 1,
        "member": {...},
    }
    """
    if not isinstance(target, dict):
        return None

    target_id = member_identity(target)
    if target_id[0] <= 0 or not target_id[1]:
        return None

    for raid_idx, raid in enumerate(raids):
        for party_name in ("party1", "party2"):
            party = raid.get(party_name, [])
            for member_idx, member in enumerate(party):
                if is_same_member(member, target):
                    return {
                        "location": "raid",
                        "raid_index": raid_idx,
                        "party_name": party_name,
                        "member_index": member_idx,
                        "member": member,
                    }

    for member_idx, member in enumerate(waiting_members):
        if is_same_member(member, target):
            return {
                "location": "waiting",
                "member_index": member_idx,
                "member": member,
            }

    for member_idx, member in enumerate(excluded_members):
        if is_same_member(member, target):
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
    if not isinstance(found, dict):
        return None

    location = found.get("location")

    if location == "raid":
        raid_index = found.get("raid_index")
        party_name = found.get("party_name")
        member_index = found.get("member_index")

        if not isinstance(raid_index, int):
            return None
        if party_name not in ("party1", "party2"):
            return None
        if not isinstance(member_index, int):
            return None
        if raid_index < 0 or raid_index >= len(raids):
            return None

        party = raids[raid_index].get(party_name, [])
        if member_index < 0 or member_index >= len(party):
            return None

        return party.pop(member_index)

    if location == "waiting":
        member_index = found.get("member_index")
        if not isinstance(member_index, int):
            return None
        if member_index < 0 or member_index >= len(waiting_members):
            return None
        return waiting_members.pop(member_index)

    if location == "excluded":
        member_index = found.get("member_index")
        if not isinstance(member_index, int):
            return None
        if member_index < 0 or member_index >= len(excluded_members):
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
    if not isinstance(member, dict):
        raise ValueError("member는 dict여야 합니다.")

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
        target_party = target_raid.get(target_party_name, [])

        if len(target_party) >= 4:
            raise ValueError("대상 파티가 이미 가득 찼습니다.")

        target_party.append(member)
        return

    raise ValueError(f"지원하지 않는 move_type: {move_type}")


def get_party_size(party: list[dict]) -> int:
    return len(party)


def is_party_full(party: list[dict], max_size: int = 4) -> bool:
    return len(party) >= max_size
