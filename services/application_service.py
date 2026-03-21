from domain.enums import ApplicationStatus, SourceType
from domain.raid_application import RaidApplication
from repositories.raid_application_repository import RaidApplicationRepository
from services.api_service import (
    BaseApiService,
    CharacterNotFoundError,
    ExternalApiRequestError,
    InvalidApiResponseError,
)
from services.raid_service import RaidService
from services.setting_service import SettingService


class ApplicationError(Exception):
    pass


class RaidNotLinkedError(ApplicationError):
    pass


class CharacterLookupError(ApplicationError):
    pass


class DuplicateApplicationError(ApplicationError):
    pass


class EntryConditionFailedError(ApplicationError):
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("\n".join(reasons))


class ApplicationService:
    def __init__(
        self,
        api_service: BaseApiService,
        setting_service: SettingService,
        raid_service: RaidService,
        raid_application_repository: RaidApplicationRepository,
    ):
        self.api_service = api_service
        self.setting_service = setting_service
        self.raid_service = raid_service
        self.raid_application_repository = raid_application_repository

    def apply(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        user_name: str,
        character_name: str,
        created_by_user_id: int | None = None,
        source_type: str = "user",
    ) -> RaidApplication:
        channel_raid = self.raid_service.get_channel_raid(channel_id)
        if channel_raid is None:
            raise RaidNotLinkedError("현재 채널에 연결된 레이드가 없어 신청할 수 없습니다.")

        duplicate = self.raid_application_repository.get_by_guild_raid_character(
            guild_id=guild_id,
            raid_name=channel_raid.raid_name,
            character_name=character_name.strip(),
        )
        if duplicate is not None:
            raise DuplicateApplicationError("이미 동일 레이드에 동일 캐릭터명으로 신청되어 있습니다.")

        setting = self.setting_service.get_guild_setting(guild_id)

        try:
            raw_data = self.api_service.get_character_info(
                character_name=character_name.strip(),
                server=setting.default_server if setting else None,
                race=setting.default_race if setting else None,
            )
            info = self.api_service.normalize_character_response(raw_data)
        except (CharacterNotFoundError, ExternalApiRequestError, InvalidApiResponseError) as exc:
            raise CharacterLookupError(str(exc)) from exc
        except Exception as exc:
            raise CharacterLookupError("캐릭터 정보를 조회할 수 없습니다.") from exc

        valid, errors = self.raid_service.validate_entry_condition(
            channel_raid=channel_raid,
            item_level=info["item_level"],
            combat_power=info["combat_power"],
        )
        if not valid:
            raise EntryConditionFailedError(errors)

        application = RaidApplication(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=channel_raid.raid_name,
            user_id=user_id,
            user_name=user_name,
            character_name=info["character_name"],
            job=info["job"],
            item_level=info["item_level"],
            combat_power=info["combat_power"],
            application_status=ApplicationStatus.APPLIED,
            source_type=SourceType(source_type),
            created_by_user_id=created_by_user_id or user_id,
        )
        return self.raid_application_repository.create(application)

    def get_my_application_in_current_channel(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
    ) -> list[RaidApplication]:
        channel_raid = self.raid_service.get_channel_raid(channel_id)
        if channel_raid is None:
            return []

        return self.raid_application_repository.get_user_application_in_raid(
            guild_id=guild_id,
            user_id=user_id,
            raid_name=channel_raid.raid_name,
        )

    def get_user_applications(self, guild_id: int, user_id: int) -> list[RaidApplication]:
        return self.raid_application_repository.get_user_applications(guild_id, user_id)

    def cancel_application(
        self,
        application_id: int,
        requester_user_id: int,
        is_admin: bool = False,
    ) -> bool:
        application = self.raid_application_repository.get_by_id(application_id)
        if application is None:
            return False

        if not is_admin and application.user_id != requester_user_id:
            raise ApplicationError("본인의 신청만 취소할 수 있습니다.")

        return self.raid_application_repository.delete_by_id(application_id)
