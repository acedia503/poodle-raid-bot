from typing import Any


class ApiService:
    def __init__(self, api_base_url: str, timeout: int = 10):
        self.api_base_url = api_base_url
        self.timeout = timeout

    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:
        # TODO: 실제 API 연동 시 교체
        # 현재는 테스트용 mock 반환
        if not character_name.strip():
            raise ValueError("캐릭터명이 비어 있습니다.")

        return {
            "character_name": character_name.strip(),
            "job": "검성",
            "item_level": 1250,
            "combat_power": 34000,
            "server": server or "기본서버",
            "race": race or "기본종족",
        }

    def normalize_character_response(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "character_name": str(raw_data["character_name"]),
            "job": str(raw_data["job"]),
            "item_level": int(raw_data["item_level"]),
            "combat_power": int(raw_data["combat_power"]),
            "server": raw_data.get("server"),
            "race": raw_data.get("race"),
        }
