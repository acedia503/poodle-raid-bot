# models.py
# Character, JOB_POLICY 같은 데이터 구조 담당

JOB_POLICY = {
    "치유성": {
        "role": "healer",
        "party2_required": True,
        "party1_priority": 1
    },
    "호법성": {
        "role": "support",
        "party2_required": False,
        "party1_priority": 2
    },
    "수호성": {
        "role": "tank",
        "party2_required": False,
        "party1_priority": 3
    },
    "검성": {
        "role": "melee",
        "party2_required": False,
        "party1_priority": 4
    },
    "살성": {
        "role": "melee",
        "party2_required": False,
        "party1_priority": 4
    },
    "궁성": {
        "role": "ranged",
        "party2_required": False,
        "party1_priority": 4
    },
    "마도성": {
        "role": "ranged",
        "party2_required": False,
        "party1_priority": 4
    },
    "정령성": {
        "role": "ranged",
        "party2_required": False,
        "party1_priority": 4
    }
}


class Character:
    def __init__(self, user_id: int, user_name: str, name: str):
        self.user_id = user_id
        self.user_name = user_name
        self.name = name

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict):
        if "user_id" not in data or "name" not in data:
            raise ValueError(f"Character 데이터가 올바르지 않습니다: {data}")

        return cls(
            user_id=data["user_id"],
            user_name=data.get("user_name", "알수없음"),
            name=data["name"]
        )

    def __repr__(self):
        return (
            f"Character(user_id={self.user_id}, "
            f"user_name='{self.user_name}', name='{self.name}')"
        )