from services.api_service import (
    BaseApiService,
    CharacterNotFoundError,
    ExternalApiRequestError,
    InvalidApiResponseError,
)


class CharacterInfoError(Exception):
    pass


class CharacterInfoService:
    def __init__(self, api_service: BaseApiService):
        self.api_service = api_service

    def get_character_info(
        self,
        character_name: str,
        race: str,
        server: str,
    ) -> dict:
        try:
            return self.api_service.get_character_info(
                character_name=character_name,
                race=race,
                server=server,
            )
        except (CharacterNotFoundError, ExternalApiRequestError, InvalidApiResponseError) as exc:
            raise CharacterInfoError(str(exc)) from exc
