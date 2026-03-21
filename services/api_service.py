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


class HttpApiService(BaseApiService):
    """
    기본 가정:
    - GET {base_url}{character_path}
    - query params: character_name, server, race
    - 인증이 필요하면 header 추가
    - 응답 예시:
      {
        "character_name": "아툴",
        "job": "검성",
        "item_level": 1250,
        "combat_power": 34000,
        "server": "루미네스",
        "race": "천족"
      }

    실제 API 스펙이 다르면 아래 3개만 바꾸면 됨:
    - _build_url
    - _build_params
    - _extract_payload
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        api_key: str | None = None,
        character_path: str = "/characters",
        auth_header_name: str | None = "Authorization",
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self.character_path = character_path
        self.auth_header_name = auth_header_name

    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:
        if not character_name.strip():
            raise CharacterNotFoundError("캐릭터명이 비어 있습니다.")

        url = self._build_url()
        headers = self._build_headers()
        params = self._build_params(
            character_name=character_name.strip(),
            server=server,
            race=race,
        )

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(
                f"외부 API 요청에 실패했습니다: {exc}"
            ) from exc

        if response.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        if response.status_code >= 400:
            raise ExternalApiRequestError(
                f"외부 API 오류가 발생했습니다. status={response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidApiResponseError("외부 API가 JSON을 반환하지 않았습니다.") from exc

        payload = self._extract_payload(data)
        return self.normalize_character_response(payload)

    def _build_url(self) -> str:
        return f"{self.base_url}{self.character_path}"

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}

        if self.api_key and self.auth_header_name:
            if self.auth_header_name.lower() == "authorization":
                headers[self.auth_header_name] = f"Bearer {self.api_key}"
            else:
                headers[self.auth_header_name] = self.api_key

        return headers

    def _build_params(
        self,
        character_name: str,
        server: str | None,
        race: str | None,
    ) -> dict[str, str]:
        params = {"character_name": character_name}

        if server:
            params["server"] = server
        if race:
            params["race"] = race

        return params

    def _extract_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        실제 API가 감싸서 주는 경우 대응:
        - {"data": {...}}
        - {"result": {...}}
        - {...}
        """
        if "data" in data and isinstance(data["data"], dict):
            return data["data"]
        if "result" in data and isinstance(data["result"], dict):
            return data["result"]
        return data
