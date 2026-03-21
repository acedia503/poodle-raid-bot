from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import requests


class ApiServiceError(Exception):
    pass


class CharacterNotFoundError(ApiServiceError):
    pass


class ExternalApiRequestError(ApiServiceError):
    pass


class InvalidApiResponseError(ApiServiceError):
    pass


class BaseApiService(ABC):
    @abstractmethod
    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def normalize_character_response(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        try:
            return {
                "character_name": str(raw_data["character_name"]).strip(),
                "job": str(raw_data["job"]).strip(),
                "item_level": int(raw_data["item_level"]),
                "combat_power": int(raw_data["combat_power"]),
                "server": raw_data.get("server"),
                "race": raw_data.get("race"),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidApiResponseError(
                "캐릭터 API 응답 형식이 예상과 다릅니다."
            ) from exc


class MockApiService(BaseApiService):
    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:
        if not character_name.strip():
            raise CharacterNotFoundError("캐릭터명이 비어 있습니다.")

        return {
            "character_name": character_name.strip(),
            "job": "검성",
            "item_level": 1250,
            "combat_power": 34000,
            "server": server or "기본서버",
            "race": race or "기본종족",
        }


import requests
from typing import Any


class HttpApiService:
    def __init__(self, timeout: int = 10):
        self.base_url = "https://aion2.plaync.com/ko-kr/api/search/aion2/search/v2/character"
        self.timeout = timeout

    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:

        params = {
            "keyword": character_name,
            "page": 1,
            "size": 1
        }

        # 👇 race 변환
        if race == "천족":
            params["race"] = 1
        elif race == "마족":
            params["race"] = 2

        # 👇 server 변환 (현재는 직접 매핑 필요)
        if server:
            params["serverId"] = self._convert_server_to_id(server)

        response = requests.get(
            self.base_url,
            params=params,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise Exception(f"API 오류: {response.status_code}")

        data = response.json()

        return self._extract_character(data)

    # --------------------------------------

    def _extract_character(self, data: dict[str, Any]) -> dict[str, Any]:
        if "list" not in data or not data["list"]:
            raise Exception("캐릭터를 찾을 수 없습니다.")

        char = data["list"][0]

        item_level = self._extract_item_level(char)

        return {
            "character_name": char["characterName"],
            "job": char["className"],
            "item_level": item_level,
            "combat_power": char["combatPower"],
            "server": char.get("serverName"),
            "race": char.get("raceName"),
        }

    # --------------------------------------

    def _extract_item_level(self, char: dict) -> int:
        stat_list = char.get("stat", {}).get("statList", [])

        for stat in stat_list:
            if stat.get("type") == "ItemLevel":
                return stat.get("value", 0)

        return 0

    # --------------------------------------

    def _convert_server_to_id(self, server_name: str) -> int:
        # TODO: 서버 목록 확장 필요
        mapping = {
            "파프니르": 2019,
        }
        return mapping.get(server_name, 2019)
