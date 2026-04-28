from repositories.raid_application_repository import RaidApplicationRepository
from repositories.character_repository import CharacterRepository
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
        character_repository: CharacterRepository,
    ):
        self.character_info_service = character_info_service
        self.setting_service = setting_service
        self.raid_service = raid_service
        self.repository = repository
        self.character_repository = character_repository

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
        channel_raid = self.raid_service.get_channel_raid(channel_id)

        info = self.character_info_service.get_character_info(
            character_name=character_name,
            race=race,
            server=server,
        )

        info_character_name = info.get("character_name") or character_name
        info_race = info.get("race") or race
        info_server = info.get("server") or server

        print("[APP][INFO]", info)
        
        existing_apps = self.repository.get_user_applications_by_character_identity(
            guild_id=guild_id,
            user_id=user_id,
            character_name=info_character_name,
            race=info_race,
            server=info_server,
        )
        
        existing_character = self.character_repository.get_by_identity(
            guild_id=guild_id,
            character_name=info_character_name,
            race=info_race,
            server=info_server,
        )
        
        if existing_character is not None and existing_character.user_id != user_id:
            return {
                "action": "already_exists_other_user",
                "raid_name": channel_raid.raid_name if channel_raid else "-",
                "message": "해당 캐릭터는 다른 유저의 캐릭터로 등록되어 있습니다. 관리자에게 문의해주세요.",
                "info": {
                    "user_name": existing_character.user_name,
                    "character_name": existing_character.character_name,
                    "race": existing_character.race,
                    "server": existing_character.server,
                    "job": existing_character.job,
                    "item_level": existing_character.item_level,
                    "combat_power": existing_character.combat_power,
                },
            }
    
        character = self.character_repository.upsert(
            guild_id=guild_id,
            user_id=user_id,
            user_name=user_name,
            character_name=info_character_name,
            race=info_race,
            server=info_server,
            job=info["job"],
            item_level=info["item_level"],
            combat_power=info["combat_power"],
        )

        self.repository.bulk_update_character_snapshot(
            applications=existing_apps,
            job=character.job,
            item_level=character.item_level,
            combat_power=character.combat_power,
        )

        if channel_raid is None:
            if not existing_apps:
                return {
                    "action": "not_allowed",
                    "message": "현재 채널에는 레이드가 설정되어 있지 않아 신청할 수 없습니다.",
                }

            return {
                "action": "show_all",
                "info": {
                    "character_name": character.character_name,
                    "race": character.race,
                    "server": character.server,
                    "job": character.job,
                    "item_level": character.item_level,
                    "combat_power": character.combat_power,
                },
                "applications": existing_apps,
            }

        existing_in_current_raid = self.repository.get_by_guild_raid_character_identity(
            guild_id=guild_id,
            raid_name=channel_raid.raid_name,
            character_name=character.character_name,
            race=character.race,
            server=character.server,
        )

        if existing_in_current_raid is not None:
            if existing_in_current_raid.user_id == user_id:
                return {
                    "action": "show_current",
                    "message": "이미 신청된 캐릭터입니다. 신청 정보를 업데이트합니다.",
                    "info": {
                        "character_name": character.character_name,
                        "race": character.race,
                        "server": character.server,
                        "job": character.job,
                        "item_level": character.item_level,
                        "combat_power": character.combat_power,
                    },
                    "raid_name": channel_raid.raid_name,
                    "application": existing_in_current_raid,
                }

            return {
                "action": "already_exists_other_user",
                "message": "이미 신청된 캐릭터입니다. 신청 정보를 조회합니다.",
                "info": {
                    "user_name": existing_in_current_raid.user_name,
                    "character_name": existing_in_current_raid.character_name,
                    "race": existing_in_current_raid.race,
                    "server": existing_in_current_raid.server,
                    "job": existing_in_current_raid.job,
                    "item_level": existing_in_current_raid.item_level,
                    "combat_power": existing_in_current_raid.combat_power,
                },
                "raid_name": channel_raid.raid_name,
                "application": existing_in_current_raid,
            }

        if (
            channel_raid.min_item_level is not None
            and character.item_level < channel_raid.min_item_level
        ):
            return {
                "action": "rejected",
                "raid_name": channel_raid.raid_name,
                "info": {
                    "character_name": character.character_name,
                    "race": character.race,
                    "server": character.server,
                    "job": character.job,
                    "item_level": character.item_level,
                    "combat_power": character.combat_power,
                    "min_item_level": channel_raid.min_item_level,
                },
                "message": "입장 조건인 아이템 레벨이 충족하지 않습니다.",
            }

        application = RaidApplication(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            user_name=user_name,
            character_name=character.character_name,
            race=character.race,
            server=character.server,
            job=character.job,
            item_level=character.item_level,
            combat_power=character.combat_power,
            raid_name=channel_raid.raid_name,
            character_id=character.id,
        )

        created = self.repository.create(application)

        return {
            "action": "created",
            "info": {
                "character_name": character.character_name,
                "race": character.race,
                "server": character.server,
                "job": character.job,
                "item_level": character.item_level,
                "combat_power": character.combat_power,
            },
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
            "info": {
                "character_name": character.character_name,
                "race": character.race,
                "server": character.server,
                "job": character.job,
                "item_level": character.item_level,
                "combat_power": character.combat_power,
            },
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
    
        character_id = application.character_id
    
        deleted = self.repository.delete_by_id(application_id)
        if not deleted:
            return False
    
        if character_id is not None:
            remaining_count = self.repository.count_by_character_id(character_id)
            if remaining_count == 0:
                self.character_repository.delete_by_id(character_id)
    
        return True


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
        applications = [
            app
            for app in (self.repository.get_by_id(app_id) for app_id in application_ids)
            if app is not None
        ]
    
        deleted_count = self.repository.delete_by_ids(application_ids)
    
        character_ids = {
            app.character_id
            for app in applications
            if app.character_id is not None
        }
    
        for character_id in character_ids:
            remaining_count = self.repository.count_by_character_id(character_id)
            if remaining_count == 0:
                self.character_repository.delete_by_id(character_id)
    
        return deleted_count

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
        
    def register_to_waiting_if_party_exists(
        self,
        guild_id: int,
        channel_id: int,
        application,
        party_manage_service,
        party_waiting_repository,
    ) -> bool:
        """
        활성 공대가 있으면 신청자를 상비군에 등록한다.
        이미 상비군/공대에 있으면 중복 등록하지 않는다.
        return: 상비군 등록 여부
        """
        raid = self.raid_service.get_channel_raid(channel_id)
        if raid is None:
            return False
    
        session = party_manage_service.get_active_session(guild_id, channel_id)
        if session is None:
            return False
    
        # 이미 상비군에 있는지 확인
        waiting_members = party_waiting_repository.get_by_session_id(session.id)
        for member in waiting_members:
            if (
                member["user_id"] == application.user_id
                and member["character_name"] == application.character_name
                and member.get("race") == application.race
                and member.get("server") == application.server
            ):
                return False
    
        # 이미 공대 슬롯에 있는지 확인
        slots = party_manage_service.party_slot_repository.get_by_session_id(session.id)
        for slot in slots:
            if (
                slot["user_id"] == application.user_id
                and slot["character_name"] == application.character_name
                and slot.get("race") == application.race
                and slot.get("server") == application.server
            ):
                return False
    
        party_waiting_repository.insert_waiting(
            session_id=session.id,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
            application_id=application.id,
            user_id=application.user_id,
            user_name=application.user_name,
            character_name=application.character_name,
            race=application.race,
            server=application.server,
            job=application.job,
            item_level=application.item_level,
            combat_power=application.combat_power,
        )
        return True
