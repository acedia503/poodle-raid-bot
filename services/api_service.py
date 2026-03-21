from typing import Any


class ApiService:
    def __init__(self, api_base_url: str, timeout: int = 10):
        self.api_base_url = api_base_url
        self.timeout = timeout

    def get_character_info(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> dict[str, Any]:
        # TODO: 실제 외부 API 호출
        # TODO: requests/httpx 중 하나로 구현
        raise NotImplementedError

    def validate_character_exists(
        self,
        character_name: str,
        server: str | None = None,
        race: str | None = None,
    ) -> bool:
        # TODO: API 호출 결과 기반 판별
        raise NotImplementedError

    def normalize_character_response(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        # TODO: API 응답 표준화
        raise NotImplementedError
