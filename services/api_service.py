from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import quote, unquote
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
        return {
            "character_name": str(raw_data.get("character_name") or "-").strip(),
            "job": str(raw_data.get("job") or "-").strip(),
            "item_level": int(raw_data.get("item_level") or 0),
            "combat_power": int(raw_data.get("combat_power") or 0),
            "server": str(raw_data.get("server") or "-").strip(),
            "race": str(raw_data.get("race") or "-").strip(),
        }


class MockApiService(BaseApiService):
    def get_character_info(self, character_name: str, server=None, race=None):
        return {
            "character_name": character_name,
            "job": "수호성",
            "item_level": 3000,
            "combat_power": 200000,
            "server": server or "-",
            "race": race or "-",
        }


class HttpApiService(BaseApiService):
    def __init__(self, timeout: int = 5):
        self.base_url = "https://aion2.plaync.com"
        self.search_url = f"{self.base_url}/ko-kr/api/search/aion2/search/v2/character"
        self.detail_url = f"{self.base_url}/api/character/info"
        self.character_page_url = f"{self.base_url}/ko-kr/characters"
        self.timeout = timeout
        self.session = requests.Session()

    def get_character_info(self, character_name: str, server=None, race=None):
        search_data = self._search_character(character_name, server, race)
        basic = self._extract_basic_character(search_data, character_name)

        detail = self._get_character_detail(
            basic["character_id"],
            basic["server_id"],
            basic["race_id"],
        )

        merged = self._merge_basic_and_detail(basic, detail)
        return self.normalize_character_response(merged)

    def _get_headers(self, referer=None, server_id=None, race_id=None):
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Referer": referer or f"{self.base_url}/ko-kr/",
        }

        if server_id and race_id:
            headers["Cookie"] = f"charactersSelectedServerId={race_id}-{server_id}"

        return headers

    def _search_character(self, name, server, race):
        params = {"keyword": name, "page": 1, "size": 10}

        if race:
            params["race"] = RACE_TO_ID[race]
        if server:
            params["serverId"] = SERVER_NAME_TO_ID[server]

        return self._request_json(self.search_url, params)["data"]

    def _get_character_detail(self, cid, sid, rid):
        decoded = unquote(cid)
        encoded = quote(decoded, safe="")

        referer = f"{self.character_page_url}/{sid}/{encoded}"

        params = {
            "lang": "ko",
            "characterId": decoded,
            "serverId": sid,
        }

        return self._request_json(
            self.detail_url,
            params,
            referer,
            sid,
            rid,
        )["data"]

    def _request_json(self, url, params, referer=None, sid=None, rid=None):
        res = self.session.get(
            url,
            params=params,
            headers=self._get_headers(referer, sid, rid),
            timeout=self.timeout,
            allow_redirects=False,
        )

        # 🔥 핵심 디버깅 로그
        print("\n====== API DEBUG ======")
        print("[URL]", url)
        print("[FINAL_URL]", res.url)
        print("[STATUS]", res.status_code)
        print("[LOCATION]", res.headers.get("Location"))
        print("[HEADERS]", dict(res.request.headers))
        print("[BODY]", res.text[:300])
        print("=======================\n")

        if res.status_code == 404:
            raise CharacterNotFoundError("캐릭터 없음")

        if res.status_code in (301, 302):
            raise ExternalApiRequestError(f"리다이렉트 발생: {res.headers.get('Location')}")

        data = res.json()
        return data

    def _extract_basic_character(self, data, keyword):
        char = data["list"][0]

        return {
            "character_id": char["characterId"],
            "server_id": char["serverId"],
            "race_id": int(char.get("race", 2)),
            "character_name": self._clean_html(char["characterName"]),
            "server": char.get("serverName"),
            "race": self._extract_race_name(char),
        }

    def _merge_basic_and_detail(self, basic, detail):
        profile = detail.get("profile", {})

        return {
            "character_name": profile.get("characterName", basic["character_name"]),
            "job": profile.get("className", "-"),
            "item_level": self._extract_item_level(detail),
            "combat_power": profile.get("combatPower", 0),
            "server": profile.get("serverName", basic["server"]),
            "race": profile.get("raceName", basic["race"]),
        }

    def _extract_item_level(self, detail):
        for s in detail.get("stat", {}).get("statList", []):
            if s.get("type") == "ItemLevel":
                return int(s.get("value", 0))
        return 0

    def _extract_race_name(self, char):
        return {1: "천족", 2: "마족"}.get(char.get("race"), "-")

    def _clean_html(self, text):
        return re.sub(r"<.*?>", "", text)
