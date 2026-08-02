from psycopg2 import errors as psycopg2_errors

from models.lol_application import LolApplication
from repositories.lol_application_repository import LolApplicationRepository


class LolApplicationService:
    def __init__(self, repository: LolApplicationRepository):
        self.repository = repository

    def _validate_and_normalize(
        self,
        riot_id: str,
    ) -> tuple[str | None, str | None]:
        """
        롤 아이디 형식을 검증하고 (표시용 riot_id, 정규화된 riot_id)를 반환한다.
        형식이 올바르지 않으면 (None, None)을 반환한다.
        """
        trimmed = riot_id.strip()

        if "#" not in trimmed:
            return None, None

        name_part, tag_part = trimmed.rsplit("#", 1)

        if not name_part.strip() or not tag_part.strip():
            return None, None

        normalized = "".join(trimmed.split()).casefold()
        return trimmed, normalized

    def apply(
        self,
        guild_id: int,
        user_id: int,
        user_name: str,
        riot_id: str,
    ) -> dict:
        """
        롤 신청/수정 처리.
        반환 action: invalid_format | duplicate | created | updated
        """
        trimmed_riot_id, normalized_riot_id = self._validate_and_normalize(riot_id)

        if trimmed_riot_id is None:
            return {"action": "invalid_format"}

        is_duplicate = self.repository.exists_by_normalized_riot_id(
            guild_id=guild_id,
            normalized_riot_id=normalized_riot_id,
            exclude_user_id=user_id,
        )
        if is_duplicate:
            return {"action": "duplicate"}

        try:
            application, is_new = self.repository.upsert(
                guild_id=guild_id,
                user_id=user_id,
                user_name=user_name,
                riot_id=trimmed_riot_id,
                normalized_riot_id=normalized_riot_id,
            )
        except psycopg2_errors.UniqueViolation:
            return {"action": "duplicate"}

        return {
            "action": "created" if is_new else "updated",
            "application": application,
        }

    def get_my_application(
        self,
        guild_id: int,
        user_id: int,
    ) -> LolApplication | None:
        return self.repository.get_by_guild_and_user_id(guild_id, user_id)

    def get_all(self, guild_id: int) -> list[LolApplication]:
        return self.repository.get_all_by_guild_id(guild_id)

    def cancel(self, guild_id: int, user_id: int) -> bool:
        return self.repository.delete_by_guild_and_user_id(guild_id, user_id)

    def count(self, guild_id: int) -> int:
        return self.repository.count_by_guild_id(guild_id)

    def reset(self, guild_id: int) -> int:
        return self.repository.delete_all_by_guild_id(guild_id)
