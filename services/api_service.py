from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import re

from curl_cffi import requests

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
        result = self.normalize_character_response(merged)

        print("[APP][INFO]", result)

        return result

    def _get_headers(self, referer: str | None = None) -> dict[str, str]:
        return {
            "Host": "aion2.plaync.com",
            "Connection": "keep-alive",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": referer or f"{self.base_url}/ko-kr/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
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

        payload = self._request_json(
            url=self.search_url,
            params=params,
            referer=f"{self.base_url}/ko-kr/characters/index",
            debug_label="SEARCH",
        )

        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]

        if not isinstance(payload, dict):
            raise InvalidApiResponseError("검색 API 응답 형식이 예상과 다릅니다.")

        return payload

    def _get_character_detail(
        self,
        character_id: str,
        server_id: int,
    ) -> dict[str, Any]:
        # character_id는 검색 API 응답 그대로 사용.
        # 예: R2A3...Txs%3D
        detail_url = (
            f"{self.detail_url}"
            f"?lang=ko&characterId={character_id}&serverId={server_id}"
        )

        referer = f"{self.character_page_url}/{server_id}/{character_id}"

        payload = self._request_json(
            url=detail_url,
            params=None,
            referer=referer,
            debug_label="DETAIL",
        )

        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]

        if not isinstance(payload, dict):
            raise InvalidApiResponseError("상세 API 응답 형식이 예상과 다릅니다.")

        print("[API][DETAIL_KEYS]", payload.keys())

        return payload

    def _request_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        referer: str | None = None,
        debug_label: str = "API",
    ) -> dict[str, Any]:
        try:
            kwargs: dict[str, Any] = {
                "headers": self._get_headers(referer),
                "timeout": self.timeout,
                "allow_redirects": False,
            }

            if params is not None:
                kwargs["params"] = params

            res = self.session.get(url, **kwargs)

        except Exception as exc:
            raise ExternalApiRequestError(f"외부 API 요청 실패: {exc}") from exc

        print(f"====== API DEBUG [{debug_label}] ======")
        print("[API][FINAL_URL]", res.url)
        print("[API][STATUS]", res.status_code)
        print("[API][LOCATION]", res.headers.get("Location"))
        print("[API][REQUEST_HEADERS]", dict(res.request.headers))
        print("[API][BODY]", res.text[:500])
        print("=======================")

        if res.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        if res.status_code in (301, 302, 303, 307, 308):
            raise ExternalApiRequestError(
                f"상세/검색 API가 리다이렉트되었습니다: {res.headers.get('Location')}"
            )

        if res.status_code >= 400:
            raise ExternalApiRequestError(f"외부 API 오류: {res.status_code}")

        try:
            return res.json()
        except ValueError as exc:
            print("[API][INVALID_JSON_BODY]", res.text[:500])
            raise InvalidApiResponseError("JSON 응답 파싱 실패") from exc

    def _extract_basic_character(
        self,
        data: dict[str, Any],
        keyword: str,
    ) -> dict[str, Any]:
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
        profile = detail.get("profile") or {}

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
            or "-"
        )

        combat_power = (
            profile.get("combatPower")
            or detail.get("combatPower")
            or 0
        )

        item_level = self._extract_item_level(detail)

        return {
            "character_name": self._clean_html(str(character_name)),
            "job": str(job).strip(),
            "item_level": int(item_level or 0),
            "combat_power": int(combat_power or 0),
            "server": profile.get("serverName") or detail.get("serverName") or basic.get("server") or "-",
            "race": profile.get("raceName") or detail.get("raceName") or basic.get("race") or "-",
        }

    def _extract_item_level(self, detail: dict[str, Any]) -> int:
        stat = detail.get("stat") or {}

        if isinstance(stat, dict):
            stat_list = stat.get("statList") or []

            for entry in stat_list:
                if not isinstance(entry, dict):
                    continue

                if entry.get("type") == "ItemLevel":
                    return int(entry.get("value") or 0)

        return int(detail.get("itemLevel") or 0)

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
