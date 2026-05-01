from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import re

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
                "character_name": str(raw_data.get("character_name") or "-").strip(),
                "job": str(raw_data.get("job") or "-").strip(),
                "item_level": int(raw_data.get("item_level") or 0),
                "combat_power": int(raw_data.get("combat_power") or 0),
                "server": str(raw_data.get("server") or "-").strip(),
                "race": str(raw_data.get("race") or "-").strip(),
            }
        except (TypeError, ValueError) as exc:
            raise InvalidApiResponseError("캐릭터 API 응답 형식이 예상과 다릅니다.") from exc


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
            "job": "수호성",
            "item_level": 3394,
            "combat_power": 247499,
            "server": server or "기본서버",
            "race": race or "기본종족",
        }


class HttpApiService(BaseApiService):
    def __init__(self, timeout: int = 10):
        self.base_url = "https://aion2tool.com"
        self.search_url = f"{self.base_url}/api/character/search"
        self.timeout = timeout
        self.session = requests.Session()

    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:
        character_name = character_name.strip()

        if not character_name:
            raise CharacterNotFoundError("캐릭터명이 비어 있습니다.")

        raw_data = self._search_character(
            character_name=character_name,
            server=server,
            race=race,
        )

        merged = self._merge_aion2tool_response(raw_data)
        result = self.normalize_character_response(merged)

        print("[APP][INFO]", result)

        return result

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
        }

    def _search_character(
        self,
        character_name: str,
        server: str | None,
        race: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "keyword": character_name,
        }

        if server:
            server_id = SERVER_NAME_TO_ID.get(server)

            if server_id is None:
                raise InvalidApiResponseError(f"알 수 없는 서버입니다: {server}")

            payload["server_id"] = server_id

        if race:
            race_id = RACE_TO_ID.get(race)

            if race_id is None:
                raise InvalidApiResponseError(f"알 수 없는 종족입니다: {race}")

            payload["race"] = race_id

        try:
            res = self.session.post(
                self.search_url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"아툴 캐릭터 조회 요청 실패: {exc}") from exc

        print("[API][ATOOL_URL]", res.url)
        print("[API][ATOOL_STATUS]", res.status_code)

        if res.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        if res.status_code >= 400:
            print("[API][ATOOL_BODY]", res.text[:500])
            raise ExternalApiRequestError(f"아툴 API 오류: {res.status_code}")

        try:
            body = res.json()
        except ValueError as exc:
            print("[API][ATOOL_INVALID_JSON]", res.text[:500])
            raise InvalidApiResponseError("아툴 API JSON 응답 파싱 실패") from exc

        if body.get("success") is False:
            message = body.get("message") or "아툴 API 조회에 실패했습니다."
            raise CharacterNotFoundError(str(message))

        data = body.get("data")

        if not isinstance(data, dict):
            raise InvalidApiResponseError("아툴 API 응답에 data 객체가 없습니다.")

        return data

    def _merge_aion2tool_response(self, data: dict[str, Any]) -> dict[str, Any]:
        character_name = (
            data.get("nickname")
            or data.get("character_name")
            or data.get("name")
            or "-"
        )

        job = (
            data.get("job")
            or data.get("className")
            or data.get("class_name")
            or "-"
        )

        # 아툴 기준:
        # combat_power  = 아이템 레벨
        # combat_power2 = 실제 전투력
        item_level = (
            data.get("item_level")
            or data.get("combat_power")
            or 0
        )

        combat_power = (
            data.get("combat_power2")
            or data.get("nc_combat_power")
            or data.get("combat_power_value")
            or 0
        )

        return {
            "character_name": self._clean_html(str(character_name)),
            "job": str(job).strip(),
            "item_level": int(item_level or 0),
            "combat_power": int(combat_power or 0),
            "server": str(data.get("server") or "-").strip(),
            "race": str(data.get("race") or "-").strip(),
        }

    def _clean_html(self, text: str) -> str:
        if not text:
            return "-"

        return re.sub(r"<.*?>", "", text).strip()
