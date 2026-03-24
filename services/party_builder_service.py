# services/party_builder_service.py

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BuildApplicant:
    application_id: int
    guild_id: int
    channel_id: int
    user_id: int
    user_name: str
    character_name: str
    race: str
    server: str
    job: str
    item_level: int
    combat_power: int
    raid_name: str
    is_assigned: bool = False


@dataclass
class BuildParty:
    group_no: int
    party_no: int
    is_temp_group: bool
    target_size: int
    priority_jobs: list[str] = field(default_factory=list)
    preferred_jobs: list[str] = field(default_factory=list)
    members: list[BuildApplicant] = field(default_factory=list)

    @property
    def total_combat_power(self) -> int:
        return sum(member.combat_power for member in self.members)

    def is_full(self) -> bool:
        return len(self.members) >= self.target_size

    def has_job(self, job: str) -> bool:
        return any(member.job == job for member in self.members)

    def add_member(self, applicant: BuildApplicant) -> None:
        self.members.append(applicant)
        applicant.is_assigned = True


@dataclass
class BuildPlan:
    full_group_count: int
    temp_group_count: int
    total_group_count: int
    assignable_count: int
    expected_waiting_count: int
    temp_group_member_count: int


@dataclass
class RefreshSummary:
    updated_count: int = 0
    failed_count: int = 0
    failed_characters: list[str] = field(default_factory=list)


@dataclass
class BuildResult:
    session_id: int
    raid_name: str
    total_applicants: int
    full_group_count: int
    temp_group_count: int
    waiting_count: int
    parties: list[BuildParty]
    waiting_members: list[BuildApplicant]
    refresh_summary: RefreshSummary


class PartyBuilderService:
    def __init__(
        self,
        raid_service,
        raid_application_repository,
        party_rule_service,
        character_info_service,
        party_build_session_repository,
        party_slot_repository,
        party_waiting_repository,
        max_refresh_concurrency: int = 5,
    ):
        self.raid_service = raid_service
        self.raid_application_repository = raid_application_repository
        self.party_rule_service = party_rule_service
        self.character_info_service = character_info_service
        self.party_build_session_repository = party_build_session_repository
        self.party_slot_repository = party_slot_repository
        self.party_waiting_repository = party_waiting_repository
        self.max_refresh_concurrency = max_refresh_concurrency

    async def build_parties(
        self,
        guild_id: int,
        channel_id: int,
        created_by: int,
    ) -> BuildResult:
        raid = self.raid_service.get_channel_raid(channel_id)
        if raid is None:
            raise ValueError("설정된 레이드가 없습니다.")

        # 1) 현재 채널 레이드 신청자 조회
        raw_applications = self.raid_application_repository.get_by_guild_channel_and_raid(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )
        applicants = [self._to_build_applicant(row) for row in raw_applications]

        # 신청자가 아예 없을 때도 결과 세션을 만들지 여부는 정책 선택 가능
        # 지금은 그냥 빈 결과를 생성하지 않고 예외 처리
        if not applicants:
            raise ValueError("신청자가 없습니다.")

        # 2) 최신 정보 병렬 갱신
        refresh_summary = await self.refresh_applications_before_build(applicants)

        # 3) 갱신된 신청자 재조회
        refreshed_raw_applications = self.raid_application_repository.get_by_guild_channel_and_raid(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )
        applicants = [self._to_build_applicant(row) for row in refreshed_raw_applications]

        # 4) 규칙 조회
        rule = self.party_rule_service.get_or_create_rule(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )

        # 5) 계획 계산
        plan = self.calculate_build_plan(len(applicants))

        # 6) 파티 생성
        parties = self.create_parties(plan, rule)

        # 7) 신청자 정렬
        applicants = self.sort_applicants(applicants)

        # 8) 우선 직업 배치
        self.assign_priority_jobs(parties, applicants)

        # 9) 일반 배치
        self.assign_remaining_members(parties, applicants)

        # 10) 미배치 인원 = 대기
        waiting_members = [a for a in applicants if not a.is_assigned]

        # 11) 결과 저장
        saved_session = self.save_build_result(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
            created_by=created_by,
            plan=plan,
            parties=parties,
            waiting_members=waiting_members,
            total_applicants=len(applicants),
        )

        return BuildResult(
            session_id=saved_session.id,
            raid_name=raid.raid_name,
            total_applicants=len(applicants),
            full_group_count=plan.full_group_count,
            temp_group_count=plan.temp_group_count,
            waiting_count=len(waiting_members),
            parties=parties,
            waiting_members=waiting_members,
            refresh_summary=refresh_summary,
        )

    async def refresh_applications_before_build(
        self,
        applicants: list[BuildApplicant],
    ) -> RefreshSummary:
        """
        신청자 최신 정보 병렬 갱신.
        실패자는 기존 정보 유지.
        """
        summary = RefreshSummary()
        semaphore = asyncio.Semaphore(self.max_refresh_concurrency)

        async def refresh_one(applicant: BuildApplicant):
            async with semaphore:
                try:
                    # NOTE:
                    # character_info_service.get_character_info(...) 시그니처를
                    # 네 실제 서비스에 맞게 조정해야 함.
                    latest_info = await asyncio.to_thread(
                        self.character_info_service.get_character_info,
                        applicant.character_name,
                        applicant.server,
                        applicant.race,
                    )

                    # NOTE:
                    # latest_info의 반환 필드명도 실제 구현체에 맞게 조정 필요
                    self.raid_application_repository.update_character_snapshot(
                        application_id=applicant.application_id,
                        job=latest_info.job,
                        item_level=latest_info.item_level,
                        combat_power=latest_info.combat_power,
                    )

                    return ("ok", applicant.character_name)
                except Exception:
                    return ("fail", applicant.character_name)

        results = await asyncio.gather(*(refresh_one(a) for a in applicants))

        for status, character_name in results:
            if status == "ok":
                summary.updated_count += 1
            else:
                summary.failed_count += 1
                summary.failed_characters.append(character_name)

        return summary

    def calculate_build_plan(self, total_count: int) -> BuildPlan:
        """
        규칙:
        - 8명당 정식 1공대
        - 남은 6~7명 -> 임시 공대 1개
        - 남은 0~5명 -> 대기
        """
        full_group_count = total_count // 8
        remain = total_count % 8

        temp_group_count = 1 if remain >= 6 else 0

        if temp_group_count == 1:
            assignable_count = full_group_count * 8 + remain
            expected_waiting_count = 0
            temp_group_member_count = remain
        else:
            assignable_count = full_group_count * 8
            expected_waiting_count = remain
            temp_group_member_count = 0

        total_group_count = full_group_count + temp_group_count

        return BuildPlan(
            full_group_count=full_group_count,
            temp_group_count=temp_group_count,
            total_group_count=total_group_count,
            assignable_count=assignable_count,
            expected_waiting_count=expected_waiting_count,
            temp_group_member_count=temp_group_member_count,
        )

    def create_parties(self, plan: BuildPlan, rule) -> list[BuildParty]:
        """
        파티 규칙은 모든 공대에 동일 반복 적용:
        - 각 공대 1파티 -> party1 규칙
        - 각 공대 2파티 -> party2 규칙
        """
        parties: list[BuildParty] = []

        # 정식 공대
        for group_no in range(1, plan.full_group_count + 1):
            parties.append(
                BuildParty(
                    group_no=group_no,
                    party_no=1,
                    is_temp_group=False,
                    target_size=4,
                    priority_jobs=list(rule.party1_priority_jobs),
                    preferred_jobs=list(rule.party1_preferred_jobs),
                )
            )
            parties.append(
                BuildParty(
                    group_no=group_no,
                    party_no=2,
                    is_temp_group=False,
                    target_size=4,
                    priority_jobs=list(rule.party2_priority_jobs),
                    preferred_jobs=list(rule.party2_preferred_jobs),
                )
            )

        # 임시 공대
        if plan.temp_group_count == 1:
            temp_group_no = plan.full_group_count + 1
            temp_count = plan.temp_group_member_count

            # 6명 -> 3:3 / 7명 -> 4:3
            party1_size = (temp_count + 1) // 2
            party2_size = temp_count // 2

            parties.append(
                BuildParty(
                    group_no=temp_group_no,
                    party_no=1,
                    is_temp_group=True,
                    target_size=party1_size,
                    priority_jobs=list(rule.party1_priority_jobs),
                    preferred_jobs=list(rule.party1_preferred_jobs),
                )
            )
            parties.append(
                BuildParty(
                    group_no=temp_group_no,
                    party_no=2,
                    is_temp_group=True,
                    target_size=party2_size,
                    priority_jobs=list(rule.party2_priority_jobs),
                    preferred_jobs=list(rule.party2_preferred_jobs),
                )
            )

        return parties

    def sort_applicants(self, applicants: list[BuildApplicant]) -> list[BuildApplicant]:
        """
        기본 정렬:
        1) 전투력 내림차순
        2) 아이템레벨 내림차순
        3) 신청 ID 오름차순
        """
        return sorted(
            applicants,
            key=lambda a: (-a.combat_power, -a.item_level, a.application_id),
        )

    def assign_priority_jobs(
        self,
        parties: list[BuildParty],
        applicants: list[BuildApplicant],
    ) -> None:
        """
        우선 직업은 해석 B:
        - 해당 파티에 우선 직업을 먼저 배치 시도
        - 없으면 미충족으로 남기고 일반 배치 단계에서 채움
        - 파티 순서대로 먼저 배치
        """
        for party in parties:
            if not party.priority_jobs:
                continue

            for priority_job in party.priority_jobs:
                if party.is_full():
                    break

                candidate = self.find_best_priority_candidate(
                    target_party=party,
                    applicants=applicants,
                    target_job=priority_job,
                    parties=parties,
                )

                if candidate is None:
                    continue

                party.add_member(candidate)

    def find_best_priority_candidate(
        self,
        target_party: BuildParty,
        applicants: list[BuildApplicant],
        target_job: str,
        parties: list[BuildParty],
    ) -> BuildApplicant | None:
        candidates: list[tuple[int, BuildApplicant]] = []

        for applicant in applicants:
            if applicant.is_assigned:
                continue
            if applicant.job != target_job:
                continue
            if self.has_same_user_in_group(
                parties=parties,
                group_no=target_party.group_no,
                user_id=applicant.user_id,
            ):
                continue

            score = self.calculate_priority_candidate_score(
                target_party=target_party,
                candidate=applicant,
                parties=parties,
            )
            candidates.append((score, applicant))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def calculate_priority_candidate_score(
        self,
        target_party: BuildParty,
        candidate: BuildApplicant,
        parties: list[BuildParty],
    ) -> int:
        score = 0

        # 같은 파티 동일 직업 최소화
        if target_party.has_job(candidate.job):
            score -= 300

        # 전투력 균형
        projected = target_party.total_combat_power + candidate.combat_power
        avg_power = self.calculate_average_party_power(parties)
        score -= abs(projected - avg_power)

        # 기본적으로 전투력이 너무 낮은 인원만 편향되지 않도록 미세 보정
        score += candidate.combat_power // 100

        return score

    def assign_remaining_members(
        self,
        parties: list[BuildParty],
        applicants: list[BuildApplicant],
    ) -> None:
        """
        일반 배치:
        - 총 전투력이 가장 낮은 파티부터 채움
        - 전투력 균형 최우선
        - 선호 직업은 가산점
        - 같은 파티 동일 직업 최소화
        - 같은 공대 동일 user_id 금지
        """
        while True:
            available_parties = [party for party in parties if not party.is_full()]
            if not available_parties:
                break

            available_parties.sort(
                key=lambda p: (p.total_combat_power, p.group_no, p.party_no)
            )
            target_party = available_parties[0]

            best_candidate = self.select_best_candidate_for_party(
                target_party=target_party,
                applicants=applicants,
                parties=parties,
            )

            if best_candidate is None:
                break

            target_party.add_member(best_candidate)

    def select_best_candidate_for_party(
        self,
        target_party: BuildParty,
        applicants: list[BuildApplicant],
        parties: list[BuildParty],
    ) -> BuildApplicant | None:
        scored_candidates: list[tuple[int, BuildApplicant]] = []

        for applicant in applicants:
            if applicant.is_assigned:
                continue

            if self.has_same_user_in_group(
                parties=parties,
                group_no=target_party.group_no,
                user_id=applicant.user_id,
            ):
                continue

            score = self.calculate_candidate_score(
                target_party=target_party,
                candidate=applicant,
                parties=parties,
            )
            scored_candidates.append((score, applicant))

        if not scored_candidates:
            return None

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return scored_candidates[0][1]

    def calculate_candidate_score(
        self,
        target_party: BuildParty,
        candidate: BuildApplicant,
        parties: list[BuildParty],
    ) -> int:
        score = 0

        # 1) 전투력 균형 최우선
        projected_power = target_party.total_combat_power + candidate.combat_power
        other_powers = [
            party.total_combat_power
            for party in parties
            if party is not target_party
        ]
        if other_powers:
            avg_other_power = sum(other_powers) / len(other_powers)
            score -= int(abs(projected_power - avg_other_power) * 10)

        # 2) 선호 직업 보너스
        if candidate.job in target_party.preferred_jobs:
            score += 50

        # 3) 같은 파티 동일 직업 최소화
        if target_party.has_job(candidate.job):
            score -= 400

        # 4) 아직 못 채운 우선 직업 보완이면 약한 보너스
        if candidate.job in self.get_unfilled_priority_jobs(target_party):
            score += 80

        # 5) 기본 전투력 미세 보정
        score += candidate.combat_power // 100

        return score

    def get_unfilled_priority_jobs(self, party: BuildParty) -> list[str]:
        if not party.priority_jobs:
            return []

        assigned_jobs = [member.job for member in party.members]
        remaining = []

        for job in party.priority_jobs:
            if job not in assigned_jobs:
                remaining.append(job)

        return remaining

    def has_same_user_in_group(
        self,
        parties: list[BuildParty],
        group_no: int,
        user_id: int,
    ) -> bool:
        """
        같은 공대(group_no) 안에 동일 user_id 중복 금지
        """
        for party in parties:
            if party.group_no != group_no:
                continue
            for member in party.members:
                if member.user_id == user_id:
                    return True
        return False

    def calculate_average_party_power(self, parties: list[BuildParty]) -> int:
        if not parties:
            return 0
        return sum(p.total_combat_power for p in parties) // len(parties)

    def save_build_result(
        self,
        guild_id: int,
        channel_id: int,
        raid_name: str,
        created_by: int,
        plan: BuildPlan,
        parties: list[BuildParty],
        waiting_members: list[BuildApplicant],
        total_applicants: int,
    ):
        from domain.party_build_session import PartyBuildSession
        from domain.party_slot import PartySlot
        from domain.party_waiting_member import PartyWaitingMember

        # 기존 활성 세션 비활성화
        self.party_build_session_repository.deactivate_existing_sessions(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name,
        )

        session = PartyBuildSession(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid_name,
            total_applicants=total_applicants,
            full_group_count=plan.full_group_count,
            temp_group_count=plan.temp_group_count,
            waiting_count=len(waiting_members),
            created_by=created_by,
            is_active=True,
        )
        session = self.party_build_session_repository.save(session)

        slots: list[PartySlot] = []
        for party in parties:
            for idx, member in enumerate(party.members, start=1):
                slots.append(
                    PartySlot(
                        id=None,
                        session_id=session.id,
                        guild_id=guild_id,
                        channel_id=channel_id,
                        raid_name=raid_name,
                        group_no=party.group_no,
                        party_no=party.party_no,
                        slot_no=idx,
                        is_temp_group=party.is_temp_group,
                        application_id=member.application_id,
                        user_id=member.user_id,
                        user_name=member.user_name,
                        character_name=member.character_name,
                        job=member.job,
                        item_level=member.item_level,
                        combat_power=member.combat_power,
                    )
                )

        waiting_rows: list[PartyWaitingMember] = []
        for member in waiting_members:
            waiting_rows.append(
                PartyWaitingMember(
                    id=None,
                    session_id=session.id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    raid_name=raid_name,
                    application_id=member.application_id,
                    user_id=member.user_id,
                    user_name=member.user_name,
                    character_name=member.character_name,
                    job=member.job,
                    item_level=member.item_level,
                    combat_power=member.combat_power,
                )
            )

        self.party_slot_repository.save_all(slots)
        self.party_waiting_repository.save_all(waiting_rows)

        return session

    def _to_build_applicant(self, row: Any) -> BuildApplicant:
        """
        RealDictRow / 객체 둘 다 대응
        """
        return BuildApplicant(
            application_id=row.id if hasattr(row, "id") else row["id"],
            guild_id=row.guild_id if hasattr(row, "guild_id") else row["guild_id"],
            channel_id=row.channel_id if hasattr(row, "channel_id") else row["channel_id"],
            user_id=row.user_id if hasattr(row, "user_id") else row["user_id"],
            user_name=row.user_name if hasattr(row, "user_name") else row["user_name"],
            character_name=row.character_name if hasattr(row, "character_name") else row["character_name"],
            race=row.race if hasattr(row, "race") else row["race"],
            server=row.server if hasattr(row, "server") else row["server"],
            job=row.job if hasattr(row, "job") else row["job"],
            item_level=row.item_level if hasattr(row, "item_level") else row["item_level"],
            combat_power=row.combat_power if hasattr(row, "combat_power") else row["combat_power"],
            raid_name=row.raid_name if hasattr(row, "raid_name") else row["raid_name"],
        )
