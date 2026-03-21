from repositories.raid_application_repository import RaidApplicationRepository
from services.character_info_service import CharacterInfoService
from services.raid_service import RaidService
from services.setting_service import SettingService
from domain.raid_application import RaidApplication


class ApplicationService:
    def __init__(
        self,
        character_info_service: CharacterInfoService,
        setting_service: SettingService,
        raid_service: RaidService,
        repository: RaidApplicationRepository,
    ):
        self.character_info_service = character_info_service
        self.setting_service = setting_service
        self.raid_service = raid_service
        self.repository = repository

    def process(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        user_name: str,
        character_name: str,
        race: str,
        server: str,
    ) -> dict:
        # 1. 최신 캐릭터 정보 조회
        info = self.character_info_service.get_character_info(
            character_name=character_name,
            race=race,
            server=server,
        )

        # 2. 기존 신청 내역 최신화
        existing_apps = self.repository.get_user_applications_by_character_identity(
            guild_id=guild_id,
            user_id=user_id,
            character_name=character_name,
            race=race,
            server=server,
        )

        self.repository.bulk_update_character_snapshot(
            applications=existing_apps,
            job=info["job"],
            item_level=info["item_level"],
            combat_power=info["combat_power"],
        )

        # 3. 현재 채널 레이드 확인
        channel_raid = self.raid_service.get_channel_raid(channel_id)

        # 4. 현재 채널에 레이드가 있는 경우
        if channel_raid is not None:
            existing_in_current_raid = self.repository.get_user_application_in_raid(
                guild_id=guild_id,
                user_id=user_id,
                character_name=character_name,
                race=race,
                server=server,
                raid_name=channel_raid.raid_name,
            )

            # 이미 현재 레이드에 신청되어 있으면 현재 레이드 신청 내역 확인
            if existing_in_current_raid is not None:
                return {
                    "action": "show_current",
                    "info": info,
                    "raid_name": channel_raid.raid_name,
                }

            # 아이템레벨 조건 검사
            if (
                channel_raid.min_item_level is not None
                and info["item_level"] < channel_raid.min_item_level
            ):
                return {
                    "action": "rejected",
                    "message": (
                        f"{channel_raid.raid_name} 신청이 불가능합니다.\n\n"
                        f"현재 아이템레벨 {info['item_level']}\n"
                        f"필요 아이템레벨 {channel_raid.min_item_level}"
                    ),
                }

            # 현재 레이드에 신청 생성
            application = RaidApplication(
                id=None,
                guild_id=guild_id,
                channel_id=channel_id,
                user_id=user_id,
                user_name=user_name,
                character_name=character_name,
                race=race,
                server=server,
                job=info["job"],
                item_level=info["item_level"],
                combat_power=info["combat_power"],
                raid_name=channel_raid.raid_name,
            )
            self.repository.create(application)

            return {
                "action": "created",
                "info": info,
                "raid_name": channel_raid.raid_name,
            }

        # 5. 현재 채널에 레이드가 없는 경우
        if not existing_apps:
            return {
                "action": "not_allowed",
                "message": "현재 채널에는 레이드가 설정되어 있지 않아 신청할 수 없습니다.",
            }

        # 6. 다른 레이드 신청 내역 전체 표시
        return {
            "action": "show_all",
            "info": info,
            "applications": existing_apps,
        }

    def cancel_application(
        self,
        application_id: int,
        requester_user_id: int,
        is_admin: bool = False,
    ) -> bool:
        application = self.repository.get_by_id(application_id)
        if application is None:
            return False

        if not is_admin and application.user_id != requester_user_id:
            raise ValueError("본인의 신청만 취소할 수 있습니다.")

        return self.repository.delete_by_id(application_id)
