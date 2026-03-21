from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import requests

from utils.constants import RACE_TO_ID, SERVER_NAME_TO_ID


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


class HttpApiService:
    def __init__(self, timeout: int = 5):
        self.base_url = "https://aion2.plaync.com/ko-kr/api/search/aion2/search/v2/character"
        self.timeout = timeout

    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:
        if not character_name.strip():
            raise CharacterNotFoundError("캐릭터명이 비어 있습니다.")

        params = {
            "keyword": character_name.strip(),
            "page": 1,
            "size": 10,
        }

        if race:
            race_id = RACE_TO_ID.get(race)
            if race_id is None:
                raise InvalidApiResponseError(f"알 수 없는 종족입니다: {race}")
            params["race"] = race_id

        if server:
            server_id = SERVER_NAME_TO_ID.get(server)
            if server_id is None:
                raise InvalidApiResponseError(f"알 수 없는 서버입니다: {server}")
            params["serverId"] = server_id

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://aion2.plaync.com/",
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"외부 API 요청 실패: {exc}") from exc

        print("AION2 REQUEST URL:", response.url)
        print("AION2 STATUS:", response.status_code)
        print("AION2 RESPONSE TEXT:", response.text[:1000])

        if response.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        if response.status_code >= 400:
            raise ExternalApiRequestError(f"외부 API 오류: {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidApiResponseError("JSON 응답 파싱 실패") from exc

        print("AION2 RAW RESPONSE:", data)
        return self._extract_character(data, character_name.strip())

    def _extract_character(self, data: dict[str, Any], keyword: str) -> dict[str, Any]:
        char_list = data.get("list", [])
        if not char_list:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        matched = None
        for char in char_list:
            if str(char.get("characterName", "")).strip() == keyword.strip():
                matched = char
                break

        if matched is None:
            matched = char_list[0]

        item_level = self._extract_item_level(matched)

        result = {
            "character_name": str(matched.get("characterName") or "-"),
            "job": str(matched.get("className") or "-"),
            "item_level": int(item_level or 0),
            "combat_power": int(matched.get("combatPower") or 0),
            "server": str(matched.get("serverName") or "-"),
            "race": str(matched.get("raceName") or "-"),
            "level": str(matched.get("characterLevel") or "-"),
        }

        print("AION2 PARSED RESULT:", result)
        return result

    def _extract_item_level(self, char: dict[str, Any]) -> int:
        stat_list = char.get("stat", {}).get("statList", [])
        for stat in stat_list:
            if stat.get("type") == "ItemLevel":
                return int(stat.get("value", 0))
        return 0
