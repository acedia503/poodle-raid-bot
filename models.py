# models.py
# Character, JOB_POLICY 같은 데이터 구조 담당

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final


JOB_POLICY: Final[dict[str, dict[str, Any]]] = {
    "치유성": {
        "role": "healer",
        "party2_required": True,
        "party1_priority": 1,
    },
    "호법성": {
        "role": "support",
        "party2_required": False,
        "party1_priority": 2,
    },
    "수호성": {
        "role": "tank",
        "party2_required": False,
        "party1_priority": 3,
    },
    "검성": {
        "role": "melee",
        "party2_required": False,
        "party1_priority": 4,
    },
    "살성": {
        "role": "melee",
        "party2_required": False,
        "party1_priority": 4,
    },
    "궁성": {
        "role": "ranged",
        "party2_required": False,
        "party1_priority": 4,
    },
    "마도성": {
        "role": "ranged",
        "party2_required": False,
        "party1_priority": 4,
    },
    "정령성": {
        "role": "ranged",
        "party2_required": False,
        "party1_priority": 4,
    },
}


@dataclass(slots=True, frozen=True)
class Character:
    user_id: int
    user_name: str
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, int):
            raise TypeError("user_id는 int여야 합니다.")

        if self.user_id <= 0:
            raise ValueError("user_id는 0보다 커야 합니다.")

        if not isinstance(self.user_name, str):
            raise TypeError("user_name은 str이어야 합니다.")

        if not isinstance(self.name, str):
            raise TypeError("name은 str이어야 합니다.")

        cleaned_user_name = self.user_name.strip()
        cleaned_name = self.name.strip()

        if not cleaned_name:
            raise ValueError("캐릭터 이름(name)은 비어 있을 수 없습니다.")

        if not cleaned_user_name:
            cleaned_user_name = "알수없음"

        object.__setattr__(self, "user_name", cleaned_user_name)
        object.__setattr__(self, "name", cleaned_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        if not isinstance(data, dict):
            raise TypeError("Character.from_dict()의 입력은 dict여야 합니다.")

        if "user_id" not in data:
            raise ValueError("Character 데이터에 user_id가 없습니다.")

        if "name" not in data:
            raise ValueError("Character 데이터에 name이 없습니다.")

        try:
            user_id = int(data["user_id"])
        except (TypeError, ValueError) as e:
            raise ValueError("user_id는 정수로 변환 가능해야 합니다.") from e

        user_name = data.get("user_name", "알수없음")
        name = data["name"]

        return cls(
            user_id=user_id,
            user_name=user_name,
            name=name,
        )
