def format_number(value: int) -> str:
    return f"{value:,}"


def format_slot_label(group_no: int, party_no: int, slot_no: int) -> str:
    return f"{group_no}공대 {party_no}파티 {slot_no}번"


def format_application_summary(application) -> str:
    return (
        f"{application.character_name} / "
        f"{application.job} / "
        f"IL {application.item_level} / "
        f"CP {format_number(application.combat_power)}"
    )
