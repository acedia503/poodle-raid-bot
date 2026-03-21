from utils.constants import VALID_RACES


def validate_race(value: str | None) -> bool:
    if value is None:
        return True
    return value in VALID_RACES


def validate_server(value: str | None) -> bool:
    if value is None:
        return True
    return bool(value.strip())


def validate_positive_int(value: int | None) -> bool:
    if value is None:
        return True
    return value >= 0
