from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import quote
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
    def __init__(self, timeout: int = 5):
        self.search_url = "https://aion2.plaync.com/ko-kr/api/search/aion2/search/v2/character"
        self.detail_url = "https://aion2.plaync.com/api/character/info"
        self.timeout = timeout

    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:
        if not character_name.strip():
            raise CharacterNotFoundError("캐릭터명이 비어 있습니다.")

        search_data = self._search_character(
            character_name=character_name.strip(),
            server=server,
            race=race,
        )

        basic = self._extract_basic_character(search_data, character_name.strip())

        detail_data = self._get_character_detail(
            character_id=basic["character_id"],
            server_id=basic["server_id"],
        )

        merged = self._merge_basic_and_detail(basic, detail_data)
        return self.normalize_character_response(merged)

    def _search_character(
        self,
        character_name: str,
        server: str | None,
        race: str | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "keyword": character_name,
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

        response = self._request_json(self.search_url, params=params)
        payload = response["data"]

        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return payload["data"]

        return payload

    
    def _get_character_detail(self, character_id: str, server_id: int) -> dict[str, Any]:
        # character_id는 검색 API에서 받은 raw 값 그대로 사용
        # requests params를 쓰면 %가 다시 인코딩될 수 있어서 URL을 직접 조립
        url = (
            f"{self.detail_url}"
            f"?lang=ko"
            f"&characterId={character_id}"
            f"&serverId={server_id}"
        )
    
        response = self._request_json_raw(url)
        payload = response["data"]
    
        print("[API][DETAIL_URL]", response["url"])
        print("[API][DETAIL_DATA]", payload)
    
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return payload["data"]
    
        return payload


    def _request_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://aion2.plaync.com/ko-kr/",
            "Origin": "https://aion2.plaync.com",
        }

        try:
            res = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"외부 API 요청 실패: {exc}") from exc

        if res.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        if res.status_code >= 400:
            print("[API][ERROR_URL]", res.url)
            print("[API][ERROR_STATUS]", res.status_code)
            print("[API][ERROR_BODY]", res.text[:500])
            raise ExternalApiRequestError(f"외부 API 오류: {res.status_code}")

        try:
            data = res.json()
        except ValueError as exc:
            raise InvalidApiResponseError("JSON 응답 파싱 실패") from exc

        return {
            "url": res.url,
            "data": data,
        }

    
    def _request_json_raw(self, url: str) -> dict[str, Any]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://aion2.plaync.com/ko-kr/",
            "Origin": "https://aion2.plaync.com",
        }
    
        try:
            res = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"외부 API 요청 실패: {exc}") from exc
    
        if res.status_code >= 400:
            print("[API][ERROR_URL]", res.url)
            print("[API][ERROR_STATUS]", res.status_code)
            print("[API][ERROR_BODY]", res.text[:500])
    
        if res.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")
    
        if res.status_code >= 400:
            raise ExternalApiRequestError(f"외부 API 오류: {res.status_code}")
    
        try:
            data = res.json()
        except ValueError as exc:
            raise InvalidApiResponseError("JSON 응답 파싱 실패") from exc
    
        return {
            "url": res.url,
            "data": data,
        }

    
    def _extract_basic_character(self, data: dict[str, Any], keyword: str) -> dict[str, Any]:
        char_list = data.get("list", [])
        if not char_list:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        matched = None
        for char in char_list:
            raw_name = self._clean_html(
                str(char.get("characterName") or char.get("name") or "")
            )
            if raw_name.strip() == keyword.strip():
                matched = char
                break

        if matched is None:
            matched = char_list[0]

        character_id = unquote(str(matched.get("characterId") or ""))
        server_id = int(matched.get("serverId") or 0)

        if not character_id or server_id <= 0:
            raise InvalidApiResponseError("캐릭터 상세 조회에 필요한 ID 정보가 없습니다.")

        return {
            "character_id": character_id,
            "server_id": server_id,
            "character_name": self._clean_html(
                str(matched.get("characterName") or matched.get("name") or "-")
            ),
            "server": str(matched.get("serverName") or "-"),
            "race": self._extract_race_name(matched),
        }

    def _merge_basic_and_detail(
        self,
        basic: dict[str, Any],
        detail: dict[str, Any],
    ) -> dict[str, Any]:
        profile = detail.get("profile", {}) if isinstance(detail, dict) else {}

        character_name = (
            profile.get("characterName")
            or basic.get("character_name")
            or "-"
        )

        job = (
            profile.get("className")
            or detail.get("className")
            or "-"
        )

        combat_power = (
            profile.get("combatPower")
            or detail.get("combatPower")
            or 0
        )

        item_level = self._extract_item_level(detail)

        server = (
            profile.get("serverName")
            or basic.get("server")
            or "-"
        )

        race = (
            profile.get("raceName")
            or basic.get("race")
            or "-"
        )
        
        print("[API][MERGE_DETAIL_KEYS]", detail.keys() if isinstance(detail, dict) else type(detail))
        print("[API][MERGE_DETAIL]", detail)
        
        return {
            "character_name": character_name,
            "job": job,
            "item_level": item_level,
            "combat_power": combat_power,
            "server": server,
            "race": race,
        }


    def _extract_item_level(self, detail: dict[str, Any]) -> int:
        # 실제 응답 구조: detail["stat"] == list[dict]
        stat_list = detail.get("stat", [])
        if isinstance(stat_list, list):
            for entry in stat_list:
                if entry.get("type") == "ItemLevel":
                    return int(entry.get("value") or 0)

        # 혹시 구조가 바뀌었을 때 fallback
        stat_obj = detail.get("stat", {})
        if isinstance(stat_obj, dict):
            nested_stat_list = stat_obj.get("statList", [])
            if isinstance(nested_stat_list, list):
                for entry in nested_stat_list:
                    if entry.get("type") == "ItemLevel":
                        return int(entry.get("value") or 0)

        return int(detail.get("itemLevel") or 0)

    def _extract_race_name(self, char: dict[str, Any]) -> str:
        if char.get("raceName"):
            return str(char["raceName"])

        race_value = char.get("race")
        race_map = {
            1: "천족",
            2: "마족",
            "1": "천족",
            "2": "마족",
        }
        return race_map.get(race_value, "-")

    def _clean_html(self, text: str) -> str:
        if not text:
            return "-"
        return re.sub(r"<.*?>", "", text).strip()
