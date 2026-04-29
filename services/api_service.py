from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import html
import json
import re
from urllib.parse import quote

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
    def __init__(self, timeout: int = 8):
        self.search_url = "https://aion2.plaync.com/ko-kr/api/search/aion2/search/v2/character"
        self.aion2tool_char_url = "https://aion2tool.com/char/serverid={server_id}/{character_name}"
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

        search_data = self._search_character(
            character_name=character_name,
            server=server,
            race=race,
        )
        basic = self._extract_basic_character(search_data, character_name)

        tool_data = self._crawl_aion2tool_character(
            character_name=basic["character_name"],
            server_id=basic["server_id"],
        )

        merged = {
            "character_name": basic["character_name"],
            "server": basic["server"],
            "race": basic["race"],
            "job": tool_data.get("job") or "-",
            "item_level": tool_data.get("item_level") or 0,
            "combat_power": tool_data.get("combat_power") or 0,
        }

        print("[API][MERGED]", merged)
        return self.normalize_character_response(merged)

    def _get_headers(self, referer: str | None = None) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,text/plain,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": referer or "https://aion2tool.com/",
        }

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

        print("[API][SEARCH_PARAMS]", params)

        try:
            res = self.session.get(
                self.search_url,
                params=params,
                headers={
                    "User-Agent": self._get_headers()["User-Agent"],
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Referer": "https://aion2.plaync.com/ko-kr/characters/index",
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"공식 검색 API 요청 실패: {exc}") from exc

        print("[API][SEARCH_URL]", res.url)
        print("[API][SEARCH_STATUS]", res.status_code)

        if res.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")
        if res.status_code >= 400:
            print("[API][SEARCH_BODY]", res.text[:500])
            raise ExternalApiRequestError(f"공식 검색 API 오류: {res.status_code}")

        try:
            payload = res.json()
        except ValueError as exc:
            raise InvalidApiResponseError("공식 검색 API JSON 파싱 실패") from exc

        print("[API][SEARCH_PAYLOAD]", payload)

        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return payload["data"]

        return payload

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

        server_id = int(matched.get("serverId") or 0)
        if server_id <= 0:
            raise InvalidApiResponseError("검색 결과에 서버 ID가 없습니다.")

        return {
            "character_name": self._clean_html(
                str(matched.get("characterName") or matched.get("name") or keyword)
            ),
            "server_id": server_id,
            "server": str(matched.get("serverName") or "-"),
            "race": self._extract_race_name(matched),
        }

    def _crawl_aion2tool_character(self, character_name: str, server_id: int) -> dict[str, Any]:
        encoded_name = quote(character_name)
        url = self.aion2tool_char_url.format(
            server_id=server_id,
            character_name=encoded_name,
        )

        headers = self._get_headers("https://aion2tool.com/")

        try:
            res = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"아툴 캐릭터 페이지 요청 실패: {exc}") from exc

        print("[API][TOOL_URL]", res.url)
        print("[API][TOOL_STATUS]", res.status_code)

        if res.status_code == 404:
            raise CharacterNotFoundError("아툴에서 캐릭터를 찾을 수 없습니다.")
        if res.status_code >= 400:
            print("[API][TOOL_BODY]", res.text[:500])
            raise ExternalApiRequestError(f"아툴 페이지 요청 오류: {res.status_code}")

        text = res.text
        parsed = self._parse_aion2tool_html(text)

        print("[API][TOOL_PARSED]", parsed)

        if not parsed.get("job") and not parsed.get("item_level") and not parsed.get("combat_power"):
            print("[API][TOOL_HTML_HEAD]", text[:1000])
            raise InvalidApiResponseError("아툴 페이지에서 캐릭터 상세 정보를 찾지 못했습니다.")

        return parsed

    def _parse_aion2tool_html(self, text: str) -> dict[str, Any]:
        decoded = html.unescape(text)

        job = self._extract_job(decoded)
        item_level = self._extract_number_by_patterns(
            decoded,
            [
                r'"item[_-]?level"\s*:\s*"?([\d,]+)"?',
                r'"itemLevel"\s*:\s*"?([\d,]+)"?',
                r"아이템\s*레벨[^0-9]{0,20}([\d,]+)",
                r"아이템레벨[^0-9]{0,20}([\d,]+)",
            ],
        )
        combat_power = self._extract_number_by_patterns(
            decoded,
            [
                r'"combat[_-]?power"\s*:\s*"?([\d,]+)"?',
                r'"combatPower"\s*:\s*"?([\d,]+)"?',
                r"전투력[^0-9]{0,20}([\d,]+)",
            ],
        )

        return {
            "job": job,
            "item_level": item_level,
            "combat_power": combat_power,
        }

    def _extract_job(self, text: str) -> str:
        job_names = [
            "수호성", "검성", "살성", "궁성",
            "마도성", "정령성", "치유성", "호법성",
        ]

        for job in job_names:
            if job in text:
                return job

        english_to_korean = {
            "Templar": "수호성",
            "Gladiator": "검성",
            "Assassin": "살성",
            "Ranger": "궁성",
            "Sorcerer": "마도성",
            "Spiritmaster": "정령성",
            "Cleric": "치유성",
            "Chanter": "호법성",
        }

        for english, korean in english_to_korean.items():
            if english in text:
                return korean

        class_match = re.search(r'"className"\s*:\s*"([^"]+)"', text)
        if class_match:
            value = class_match.group(1)
            return english_to_korean.get(value, value)

        return "-"

    def _extract_number_by_patterns(self, text: str, patterns: list[str]) -> int:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw = match.group(1).replace(",", "")
                try:
                    return int(raw)
                except ValueError:
                    continue
        return 0

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
