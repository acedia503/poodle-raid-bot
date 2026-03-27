# services/party_builder_service.py

import asyncio
from domain.party_build_session import PartyBuildSession
from domain.party_waiting_member import PartyWaitingMember
from domain.party_slot import PartySlot


class PartyBuilderService:
    def __init__(
        self,
        raid_service,
        application_service,
        character_info_service,
        session_repository,
        slot_repository,
        waiting_repository,
    ):
        self.raid_service = raid_service
        self.application_service = application_service
        self.character_info_service = character_info_service
        self.session_repository = session_repository
        self.slot_repository = slot_repository
        self.waiting_repository = waiting_repository

    # =========================
    # 공통: 신청자 최신 정보 갱신 (병렬)
    # =========================
    async def _refresh_applicants(self, applications: list):
        async def fetch(app):
            try:
                info = await asyncio.to_thread(
                    self.character_info_service.get_character_info,
                    app.character_name,
                    app.race,
                    app.server,
                )
    
                app.job = info["job"]
                app.item_level = info["item_level"]
                app.combat_power = info["combat_power"]
    
                # DB snapshot 반영
                self.application_service.repository.update_character_snapshot(
                    application_id=app.id,
                    job=app.job,
                    item_level=app.item_level,
                    combat_power=app.combat_power,
                )
    
                print(
                    f"[API 조회 성공] {app.character_name} / "
                    f"{app.job} / {app.item_level} / {app.combat_power}"
                )
    
            except Exception as e:
                print(
                    f"[API 조회 실패] {app.character_name} / "
                    f"race={app.race} / server={app.server} / error={e}"
                )
    
        await asyncio.gather(*(fetch(app) for app in applications))

    # =========================
    # 자동 생성
    # =========================
    async def build_parties(
        self,
        guild_id: int,
        channel_id: int,
        created_by: int,
    ):
        raid = self.raid_service.get_channel_raid(channel_id)
        if raid is None:
            raise Exception("레이드 없음")

        applications = self.application_service.get_applications(
            guild_id=guild_id,
            channel_id=channel_id,
        )

        if not applications:
            raise Exception("신청자가 없습니다.")

        # 🔥 최신 정보 갱신
        await self._refresh_applicants(applications)

        # 기존 세션 제거
        self.session_repository.deactivate_existing_sessions(
            guild_id,
            channel_id,
            raid.raid_name,
        )

        total = len(applications)
        full_group_count = total // 8
        remainder = total % 8

        # 세션 생성
        session = PartyBuildSession(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
            total_applicants=total,
            full_group_count=full_group_count,
            temp_group_count=0,
            waiting_count=0,
            created_by=created_by,
            is_active=True,
        )
        session = self.session_repository.save(session)

        # 🔥 전투력 기준 정렬
        applications.sort(key=lambda x: x.combat_power, reverse=True)

        slots = []
        waiting = []

        index = 0

        # 공대 생성
        for group_no in range(1, full_group_count + 1):
            for party_no in [1, 2]:
                for slot_no in range(1, 5):
                    if index >= len(applications):
                        break

                    app = applications[index]

                    slots.append(
                        PartySlot(
                            id=None,
                            session_id=session.id,
                            guild_id=guild_id,
                            channel_id=channel_id,
                            raid_name=raid.raid_name,
                            group_no=group_no,
                            party_no=party_no,
                            slot_no=slot_no,
                            application_id=app.id,
                            user_id=app.user_id,
                            user_name=app.user_name,
                            character_name=app.character_name,
                            job=app.job,
                            item_level=app.item_level,
                            combat_power=app.combat_power,
                        )
                    )
                    index += 1

        # 나머지 → 상비군
        for i in range(index, len(applications)):
            app = applications[i]

            waiting.append(
                PartyWaitingMember(
                    id=None,
                    session_id=session.id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    raid_name=raid.raid_name,
                    application_id=app.id,
                    user_id=app.user_id,
                    user_name=app.user_name,
                    character_name=app.character_name,
                    job=app.job,
                    item_level=app.item_level,
                    combat_power=app.combat_power,
                )
            )

        self.slot_repository.save_all(slots)
        self.waiting_repository.save_all(waiting)

        return session

    # =========================
    # 수동 생성
    # =========================
    async def build_empty_parties(
        self,
        guild_id: int,
        channel_id: int,
        created_by: int,
    ):
        raid = self.raid_service.get_channel_raid(channel_id)
        if raid is None:
            raise Exception("레이드 없음")

        applications = self.application_service.get_applications(
            guild_id=guild_id,
            channel_id=channel_id,
        )

        if not applications:
            raise Exception("신청자가 없습니다.")

        # 🔥 최신 정보 갱신
        await self._refresh_applicants(applications)

        self.session_repository.deactivate_existing_sessions(
            guild_id,
            channel_id,
            raid.raid_name,
        )

        total = len(applications)
        full_group_count = total // 8

        session = PartyBuildSession(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
            total_applicants=total,
            full_group_count=full_group_count,
            temp_group_count=0,
            waiting_count=total,
            created_by=created_by,
            is_active=True,
        )
        session = self.session_repository.save(session)

        # 🔥 모든 인원 상비군
        waiting = []

        for app in applications:
            waiting.append(
                PartyWaitingMember(
                    id=None,
                    session_id=session.id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    raid_name=raid.raid_name,
                    application_id=app.id,
                    user_id=app.user_id,
                    user_name=app.user_name,
                    character_name=app.character_name,
                    job=app.job,
                    item_level=app.item_level,
                    combat_power=app.combat_power,
                )
            )

        self.waiting_repository.save_all(waiting)

        return session
