# services/party_builder_service.py

import asyncio
from dataclasses import dataclass, field

from domain.party_build_session import PartyBuildSession
from domain.party_waiting_member import PartyWaitingMember
from domain.party_slot import PartySlot


@dataclass
class PartyBucket:
    group_no: int
    party_no: int
    priority_jobs: list[str] = field(default_factory=list)
    preferred_jobs: list[str] = field(default_factory=list)
    members: list = field(default_factory=list)
    total_combat_power: int = 0

    def can_add(self) -> bool:
        return len(self.members) < 4

    def add_member(self, app) -> None:
        self.members.append(app)
        self.total_combat_power += app.combat_power


class PartyBuilderService:
    def __init__(
        self,
        raid_service,
        application_service,
        character_info_service,
        party_rule_service,
        session_repository,
        slot_repository,
        waiting_repository,
    ):
        self.raid_service = raid_service
        self.application_service = application_service
        self.character_info_service = character_info_service
        self.party_rule_service = party_rule_service
        self.session_repository = session_repository
        self.slot_repository = slot_repository
        self.waiting_repository = waiting_repository

    # =========================
    # 공통: 신청자 최신 정보 갱신
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
    # 직업 중복 수 계산
    # =========================
    def _job_duplicate_count(self, app, target_party: PartyBucket) -> int:
        return sum(1 for member in target_party.members if member.job == app.job)

    # =========================
    # 같은 직업 3중복 금지 + 2중복 최소화 후보 필터
    # =========================
    def _filter_candidates_by_job_duplication(
        self,
        app,
        candidates: list[PartyBucket],
    ) -> list[PartyBucket]:
        if not candidates:
            return []

        zero_dup = []
        one_dup = []

        for party in candidates:
            dup_count = self._job_duplicate_count(app, party)

            # 3중복 금지: 이미 2명 있으면 후보 제외
            if dup_count >= 2:
                continue

            # 같은 직업 없는 파티 최우선
            if dup_count == 0:
                zero_dup.append(party)
            else:
                one_dup.append(party)

        # 0중복 후보가 있으면 무조건 그것만 사용
        if zero_dup:
            return zero_dup

        # 0중복이 없을 때만 1중복 후보 허용
        if one_dup:
            return one_dup

        # 이론상 여기 오면 모든 후보가 2중복 상태
        # = 3중복밖에 답이 없다는 뜻이지만, 사용자 요구상 허용하지 않음
        return []

    # =========================
    # 파티 점수 계산
    # =========================
    def _calculate_party_score(
        self,
        app,
        target_party: PartyBucket,
        all_parties: list[PartyBucket],
    ) -> int:
        simulated_powers = []

        for party in all_parties:
            if party is target_party:
                simulated_powers.append(party.total_combat_power + app.combat_power)
            else:
                simulated_powers.append(party.total_combat_power)

        avg_power = sum(simulated_powers) / len(simulated_powers) if simulated_powers else 0
        balance_penalty = sum(abs(power - avg_power) for power in simulated_powers)

        score = -balance_penalty

        # 우선 직업 가산점
        if app.job in target_party.priority_jobs:
            score += 300

        # 선호 직업 가산점
        if app.job in target_party.preferred_jobs:
            score += 80

        # 동일 직업 중복 감점
        duplicate_count = self._job_duplicate_count(app, target_party)

        # 2번째 배치도 최대한 꺼리게 강한 감점
        if duplicate_count == 1:
            score -= 450

        # 3번째 배치는 후보 필터에서 이미 제외되지만, 안전장치
        elif duplicate_count >= 2:
            score -= 100000

        # 인원 적은 파티 약간 우대
        score -= len(target_party.members) * 20

        return score

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
            raise Exception("레이드가 없습니다.")

        applications = self.application_service.get_applications(
            guild_id=guild_id,
            channel_id=channel_id,
        )

        if not applications:
            raise Exception("신청자가 없습니다.")

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
            waiting_count=0,
            created_by=created_by,
            is_active=True,
        )
        session = self.session_repository.save(session)

        rule = self.party_rule_service.get_or_create_rule(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )

        party_buckets: list[PartyBucket] = []
        for group_no in range(1, full_group_count + 1):
            party_buckets.append(
                PartyBucket(
                    group_no=group_no,
                    party_no=1,
                    priority_jobs=list(rule.party1_priority_jobs),
                    preferred_jobs=list(rule.party1_preferred_jobs),
                )
            )
            party_buckets.append(
                PartyBucket(
                    group_no=group_no,
                    party_no=2,
                    priority_jobs=list(rule.party2_priority_jobs),
                    preferred_jobs=list(rule.party2_preferred_jobs),
                )
            )

        applications.sort(key=lambda x: x.combat_power, reverse=True)

        assign_count = full_group_count * 8
        assign_targets = applications[:assign_count]
        waiting_targets = applications[assign_count:]

        for app in assign_targets:
            candidates = [p for p in party_buckets if p.can_add()]
            if not candidates:
                break

            # 같은 직업 3중복 금지 + 2중복 최소화
            filtered_candidates = self._filter_candidates_by_job_duplication(app, candidates)

            if not filtered_candidates:
                raise Exception(
                    f"{app.character_name}({app.job}) 배치 불가: "
                    "같은 직업 3중복 없이 배치할 수 있는 파티가 없습니다."
                )

            best_party = max(
                filtered_candidates,
                key=lambda p: self._calculate_party_score(app, p, party_buckets),
            )

            best_party.add_member(app)

        slots = []
        for party in party_buckets:
            for slot_no, app in enumerate(party.members, start=1):
                slots.append(
                    PartySlot(
                        id=None,
                        session_id=session.id,
                        guild_id=guild_id,
                        channel_id=channel_id,
                        raid_name=raid.raid_name,
                        group_no=party.group_no,
                        party_no=party.party_no,
                        slot_no=slot_no,
                        is_temp_group=False,
                        application_id=app.id,
                        user_id=app.user_id,
                        user_name=app.user_name,
                        character_name=app.character_name,
                        job=app.job,
                        item_level=app.item_level,
                        combat_power=app.combat_power,
                    )
                )

        waiting = []
        for app in waiting_targets:
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
