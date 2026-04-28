from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import re
from urllib.parse import unquote, quote

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
        self.character_page_url = "https://aion2.plaync.com/ko-kr/characters"
        self.timeout = timeout
        self.session = requests.Session()

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
            race_id=basic.get("race_id"),
        )

        merged = self._merge_basic_and_detail(basic, detail_data)
        return self.normalize_character_response(merged)

    def _get_headers(self, referer: str | None = None) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": referer or "https://aion2.plaync.com/ko-kr/",
            "Origin": "https://aion2.plaync.com",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

    def _build_cookie_header(self, race_id: int | None, server_id: int) -> str:
        selected_server_id = f"{race_id}-{server_id}" if race_id else str(server_id)

        return (
            "gw_locale=ko-KR; "
            "aion2_gw_locale=ko-KR; "
            "visitedGame=AION2; "
            "_gcl_au=1.1.718781253.1777368849; "
            "_ga=GA1.1.101173522.1777368849; "
            f"charactersSelectedServerId={selected_server_id}; "
            "ncBannerfloating20260407=true; "
            "_ga_JMPDHRVRRL=GS2.1.s1777374888$o2$g0$t1777374888$j60$l0$h0"
        )

    def _search_character(
        self,
        character_name: str,
        server: str | None,
        race: str | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "keyword": character_name.strip(),  # 입력받은 캐릭터명
            "page": 1,
            "size": 10,
        }
    
        if race:
            race_id = RACE_TO_ID.get(race)
            if race_id is None:
                raise InvalidApiResponseError(f"알 수 없는 종족입니다: {race}")
    
            params["race"] = race_id  # 입력받은 종족 → 종족 ID
    
        if server:
            server_id = SERVER_NAME_TO_ID.get(server)
            if server_id is None:
                raise InvalidApiResponseError(f"알 수 없는 서버입니다: {server}")
    
            params["serverId"] = server_id  # 입력받은 서버 → 서버 ID
    
        print("[API][SEARCH_PARAMS]", params)
    
        response = self._request_json(
            self.search_url,
            params=params,
        )
    
        payload = response["data"]
    
        print("[API][SEARCH_URL]", response["url"])
        print("[API][SEARCH_PAYLOAD]", payload)
    
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return payload["data"]
    
        return payload

    def _warmup_character_page(
        self,
        character_id: str,
        server_id: int,
        race_id: int | None = None,
    ) -> str:
        decoded_character_id = unquote(character_id)
        encoded_character_id = quote(decoded_character_id, safe="")
        page_url = f"{self.character_page_url}/{server_id}/{encoded_character_id}"

        cookie_header = self._build_cookie_header(race_id, server_id)

        for item in cookie_header.split("; "):
            key, value = item.split("=", 1)
            self.session.cookies.set(key, value, domain=".plaync.com")

        headers = self._get_headers("https://aion2.plaync.com/ko-kr/")
        headers["Cookie"] = cookie_header

        try:
            res = self.session.get(
                page_url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"캐릭터 상세 페이지 요청 실패: {exc}") from exc

        print("[API][WARMUP_URL]", res.url)
        print("[API][WARMUP_STATUS]", res.status_code)
        print("[API][COOKIE]", self.session.cookies.get_dict())

        return page_url

    def _get_character_detail(
        self,
        character_id: str,
        server_id: int,
        race_id: int | None = None,
    ) -> dict[str, Any]:
        self._warmup_character_page(
            character_id=character_id,
            server_id=server_id,
            race_id=race_id,
        )

        decoded_character_id = unquote(character_id)
        encoded_character_id = quote(decoded_character_id, safe="")

        referer = (
            f"https://aion2.plaync.com/ko-kr/characters/"
            f"{server_id}/{encoded_character_id}"
        )

        params = {
            "lang": "ko",
            "characterId": decoded_character_id,
            "serverId": server_id,
        }

        headers = self._get_headers(referer)
        headers["Cookie"] = self._build_cookie_header(race_id, server_id)
        headers.pop("Origin", None)

        try:
            res = self.session.get(
                self.detail_url,
                params=params,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise ExternalApiRequestError(f"캐릭터 상세 API 요청 실패: {exc}") from exc
            
        print("[API][DETAIL_REQUEST_REFERER]", res.request.headers.get("Referer"))
        print("[API][DETAIL_REQUEST_HEADERS]", dict(res.request.headers))
        print("[API][DETAIL_REFERER]", referer)
        print("[API][DETAIL_URL]", res.url)
        print("[API][DETAIL_STATUS]", res.status_code)
        print("[API][DETAIL_LOCATION]", res.headers.get("Location"))
        print("[API][DETAIL_REQUEST_COOKIE]", res.request.headers.get("Cookie"))

        if res.status_code in (301, 302, 303, 307, 308):
            raise ExternalApiRequestError(
                f"상세 API가 리다이렉트되었습니다: {res.headers.get('Location')}"
            )

        if res.status_code == 404:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        if res.status_code >= 400:
            print("[API][DETAIL_BODY]", res.text[:500])
            raise ExternalApiRequestError(f"외부 API 오류: {res.status_code}")

        try:
            payload = res.json()
        except ValueError as exc:
            raise InvalidApiResponseError("JSON 응답 파싱 실패") from exc

        print("[API][DETAIL_PAYLOAD]", payload)

        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return payload["data"]

        return payload

    def _request_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            res = self.session.get(
                url,
                params=params,
                headers=self._get_headers(),
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

        character_id = str(matched.get("characterId") or "")
        server_id = int(matched.get("serverId") or 0)
        race_id_raw = matched.get("race")

        try:
            race_id = int(race_id_raw) if race_id_raw is not None else None
        except (TypeError, ValueError):
            race_id = None

        if not character_id or server_id <= 0:
            raise InvalidApiResponseError("캐릭터 상세 조회에 필요한 ID 정보가 없습니다.")

        return {
            "character_id": character_id,
            "server_id": server_id,
            "race_id": race_id,
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

        character_name = profile.get("characterName") or basic.get("character_name") or "-"
        job = profile.get("className") or detail.get("className") or "-"
        combat_power = profile.get("combatPower") or detail.get("combatPower") or 0
        item_level = self._extract_item_level(detail)
        server = profile.get("serverName") or basic.get("server") or "-"
        race = profile.get("raceName") or basic.get("race") or "-"

        return {
            "character_name": character_name,
            "job": job,
            "item_level": item_level,
            "combat_power": combat_power,
            "server": server,
            "race": race,
        }

    def _extract_item_level(self, detail: dict[str, Any]) -> int:
        stat_obj = detail.get("stat", {})

        if isinstance(stat_obj, dict):
            stat_list = stat_obj.get("statList", [])
            if isinstance(stat_list, list):
                for entry in stat_list:
                    if entry.get("type") == "ItemLevel":
                        return int(entry.get("value") or 0)

        if isinstance(stat_obj, list):
            for entry in stat_obj:
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
