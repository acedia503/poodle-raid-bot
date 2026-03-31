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
        info = self.character_info_service.get_character_info(
            character_name=character_name,
            race=race,
            server=server,
        )

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

        channel_raid = self.raid_service.get_channel_raid(channel_id)

        if channel_raid is not None:
            existing_in_current_raid = self.repository.get_user_application_in_raid(
                guild_id=guild_id,
                user_id=user_id,
                character_name=character_name,
                race=race,
                server=server,
                raid_name=channel_raid.raid_name,
            )

            if existing_in_current_raid is not None:
                return {
                    "action": "show_current",
                    "info": info,
                    "raid_name": channel_raid.raid_name,
                    "application": existing_in_current_raid,
                }

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
            created = self.repository.create(application)

            return {
                "action": "created",
                "info": info,
                "raid_name": channel_raid.raid_name,
                "application": created,
            }

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


    def get_current_raid_application_list(
        self,
        channel_id: int,
    ) -> dict:
        channel_raid = self.raid_service.get_channel_raid(channel_id)
        if channel_raid is None:
            return {
                "raid_name": None,
                "applications": [],
            }

        applications = self.repository.get_by_guild_and_raid_name(
            guild_id=channel_raid.guild_id,
            raid_name=channel_raid.raid_name,
        )

        return {
            "raid_name": channel_raid.raid_name,
            "applications": applications,
        }

    
    def search_current_raid_users(
        self,
        channel_id: int,
        keyword: str,
    ) -> dict:
        channel_raid = self.raid_service.get_channel_raid(channel_id)
        if channel_raid is None:
            return {
                "raid_name": None,
                "users": [],
            }

        users = self.repository.search_distinct_users_by_guild_raid_and_keyword(
            guild_id=channel_raid.guild_id,
            raid_name=channel_raid.raid_name,
            keyword=keyword,
        )

        return {
            "raid_name": channel_raid.raid_name,
            "users": users,
        }

    
    def search_current_raid_applications_by_user(
        self,
        channel_id: int,
        user_id: int,
    ) -> dict:
        channel_raid = self.raid_service.get_channel_raid(channel_id)
        if channel_raid is None:
            return {
                "raid_name": None,
                "applications": [],
            }

        applications = self.repository.get_by_guild_raid_and_user_id(
            guild_id=channel_raid.guild_id,
            raid_name=channel_raid.raid_name,
            user_id=user_id,
        )

        return {
            "raid_name": channel_raid.raid_name,
            "applications": applications,
        }

    def search_current_raid_applications_by_character(
        self,
        channel_id: int,
        character_name: str,
    ) -> dict:
        channel_raid = self.raid_service.get_channel_raid(channel_id)
        if channel_raid is None:
            return {
                "raid_name": None,
                "applications": [],
            }

        applications = self.repository.get_by_guild_raid_and_character_name(
            guild_id=channel_raid.guild_id,
            raid_name=channel_raid.raid_name,
            character_name=character_name,
        )

        return {
            "raid_name": channel_raid.raid_name,
            "applications": applications,
        }

    def admin_delete_applications(self, application_ids: list[int]) -> int:
        return self.repository.delete_by_ids(application_ids)

    def get_applications(
        self,
        guild_id: int,
        channel_id: int,
    ):
        """
        현재 채널(레이드)의 신청 목록 조회
        """
        raid = self.raid_service.get_channel_raid(channel_id)
        if raid is None:
            return []
    
        return self.repository.get_by_guild_and_raid_name(
            guild_id=guild_id,
            raid_name=raid.raid_name,
        )
