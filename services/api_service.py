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
    def __init__(self, timeout: int = 5):
        self.base_url = "https://aion2.plaync.com"
        self.search_url = f"{self.base_url}/ko-kr/api/search/aion2/search/v2/character"
        self.detail_url = f"{self.base_url}/api/character/info"
        self.character_page_url = f"{self.base_url}/ko-kr/characters"
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

        search_data = self._search_character(character_name, server, race)
        basic = self._extract_basic_character(search_data, character_name)

        detail_data = self._get_character_detail(
            character_id=basic["character_id"],
            server_id=basic["server_id"],
        )

        merged = self._merge_basic_and_detail(basic, detail_data)
        return self.normalize_character_response(merged)

    def _get_headers(self, referer: str | None = None) -> dict[str, str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        if referer:
            headers["Referer"] = referer
        else:
            headers["Referer"] = f"{self.base_url}/ko-kr/"

        return headers

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

        res = self._request_json(
            url=self.search_url,
            params=params,
            referer=f"{self.base_url}/ko-kr/characters",
        )

        payload = res["data"]

        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return payload["data"]

        if not isinstance(payload, dict):
            raise InvalidApiResponseError("검색 API 응답 형식이 예상과 다릅니다.")

        return payload

    def _get_character_detail(
        self,
        character_id: str,
        server_id: int,
    ) -> dict[str, Any]:
        referer = f"{self.character_page_url}/{server_id}/{character_id}"
    
        params = {
            "lang": "ko",
            "characterId": character_id,
            "serverId": server_id,
        }
    
        res = self._request_json(
            url=self.detail_url,
            params=params,
            referer=referer,
        )
    
        payload = res["data"]
    
        print("[API][RAW_DETAIL_PAYLOAD]", payload)
    
        if isinstance(payload, dict):
            if isinstance(payload.get("data"), dict):
                payload = payload["data"]
    
            if isinstance(payload.get("character"), dict):
                return payload["character"]
    
            if isinstance(payload.get("profile"), dict):
                return payload
    
            return payload
    
        raise InvalidApiResponseError("상세 API 응답 형식이 예상과 다릅니다.")

    def _request_json(
        self,
        url: str,
        params: dict[str, Any],
        referer: str | None = None,
    ) -> dict[str, Any]:
        try:
            res = self.session.get(
                url,
                params=params,
                headers=self._get_headers(referer),
                timeout=self.timeout,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"외부 API 요청 실패: {exc}") from exc

        print("[API][URL]", res.url)
        print("[API][STATUS]", res.status_code)

        if res.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        if res.status_code >= 400:
            print("[API][ERROR_BODY]", res.text[:500])
            raise ExternalApiRequestError(f"외부 API 오류: {res.status_code}")

        try:
            data = res.json()
        except ValueError as exc:
            print("[API][INVALID_JSON_BODY]", res.text[:500])
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
    
        character_name = self._clean_html(
            str(matched.get("characterName") or matched.get("name") or "-")
        )
    
        character_id = str(matched.get("characterId") or "")
        server_id = int(matched.get("serverId") or 0)
    
        if not character_id or server_id <= 0:
            raise InvalidApiResponseError("캐릭터 ID 또는 서버 ID가 없습니다.")
    
        return {
            "character_id": character_id,
            "server_id": server_id,
            "character_name": character_name,
            "server": str(matched.get("serverName") or "-"),
            "race": self._extract_race_name(matched),
        }
    
    def _merge_basic_and_detail(
        self,
        basic: dict[str, Any],
        detail: dict[str, Any],
    ) -> dict[str, Any]:
        profile = detail.get("profile", {}) if isinstance(detail, dict) else {}

        print("[API][MERGE_DETAIL_KEYS]", detail.keys() if isinstance(detail, dict) else None)
        print("[API][MERGE_DETAIL]", detail)
        
        character_name = (
            profile.get("characterName")
            or detail.get("characterName")
            or basic.get("character_name")
            or "-"
        )
    
        job = (
            profile.get("className")
            or profile.get("jobName")
            or detail.get("className")
            or detail.get("jobName")
            or detail.get("job")
            or "-"
        )
    
        combat_power = (
            profile.get("combatPower")
            or detail.get("combatPower")
            or self._extract_stat_value(detail, "CombatPower")
            or self._extract_stat_value(detail, "Power")
            or 0
        )
    
        item_level = (
            detail.get("itemLevel")
            or profile.get("itemLevel")
            or self._extract_stat_value(detail, "ItemLevel")
            or 0
        )
    
        return {
            "character_name": self._clean_html(str(character_name)),
            "job": str(job).strip(),
            "item_level": int(item_level or 0),
            "combat_power": int(combat_power or 0),
            "server": profile.get("serverName") or basic.get("server") or "-",
            "race": profile.get("raceName") or basic.get("race") or "-",
        }
    
    def _extract_stat_value(self, detail: dict[str, Any], stat_type: str) -> int:
        stat_obj = detail.get("stat", {})
    
        candidates = []
    
        if isinstance(stat_obj, dict):
            candidates.extend(stat_obj.get("statList", []))
            candidates.extend(stat_obj.get("battleStatList", []))
            candidates.extend(stat_obj.get("basicStatList", []))
    
        elif isinstance(stat_obj, list):
            candidates.extend(stat_obj)
    
        for entry in candidates:
            if not isinstance(entry, dict):
                continue
    
            if entry.get("type") == stat_type or entry.get("statType") == stat_type:
                return int(entry.get("value") or entry.get("statValue") or 0)
    
        return 0
    
    def _extract_race_name(self, char: dict[str, Any]) -> str:
        if char.get("raceName"):
            return str(char["raceName"])
    
        race_value = char.get("race")
        return {
            1: "천족",
            2: "마족",
            "1": "천족",
            "2": "마족",
        }.get(race_value, "-")
    
    def _clean_html(self, text: str) -> str:
        if not text:
            return "-"
    
        return re.sub(r"<.*?>", "", text).strip()
