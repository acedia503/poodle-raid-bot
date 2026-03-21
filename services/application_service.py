from domain.raid_application import RaidApplication
from services.character_info_service import CharacterInfoService
from services.setting_service import SettingService
from services.raid_service import RaidService
from repositories.raid_application_repository import RaidApplicationRepository


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
    ):
        # 1. 최신 정보 조회
        info = self.character_info_service.get_character_info(
            character_name=character_name,
            race=race,
            server=server,
        )

        # 2. 기존 신청 최신화
        existing_apps = self.repository.get_user_applications_by_character_identity(
            guild_id, user_id, character_name, race, server
        )

        self.repository.bulk_update_character_snapshot(
            existing_apps,
            job=info["job"],
            item_level=info["item_level"],
            combat_power=info["combat_power"],
        )

        # 3. 현재 채널 레이드
        channel_raid = self.raid_service.get_channel_raid(channel_id)

        # 4. 분기
        if channel_raid:
            existing = self.repository.get_user_application_in_raid(
                guild_id,
                user_id,
                character_name,
                race,
                server,
                channel_raid.raid_name,
            )

            # 이미 신청 있음 → 조회
            if existing:
                return {
                    "action": "show_current",
                    "info": info,
                    "raid_name": channel_raid.raid_name,
                }

            # 조건 검사
            if (
                channel_raid.min_item_level
                and info["item_level"] < channel_raid.min_item_level
            ):
                return {
                    "action": "rejected",
                    "message": f"아이템레벨 부족 (현재 {info['item_level']} / 필요 {channel_raid.min_item_level})",
                }

            # 생성
            app = RaidApplication(
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

            self.repository.create(app)

            return {
                "action": "created",
                "info": info,
                "raid_name": channel_raid.raid_name,
            }

        # 레이드 없음
        if not existing_apps:
            return {
                "action": "not_allowed",
                "message": "현재 채널에는 레이드가 설정되어 있지 않아 신청할 수 없습니다.",
            }

        return {
            "action": "show_all",
            "info": info,
            "applications": existing_apps,
        }
