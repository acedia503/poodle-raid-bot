def validate_race(value: str) -> bool:
    return value in {"천족", "마족"}


def validate_server(value: str) -> bool:
    return bool(value and value.strip())


def validate_positive_int(value: int | None) -> bool:
    return value is not None and value > 0


def validate_slot_position(
    group_no: int,
    party_no: int,
    slot_no: int,
    party_count: int = 2,
    slots_per_party: int = 4,
) -> bool:
    return group_no > 0 and 1 <= party_no <= party_count and 1 <= slot_no <= slots_per_party
