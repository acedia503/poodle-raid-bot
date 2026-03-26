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

        raw_applications = self.raid_application_repository.get_by_guild_channel_and_raid(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )
        applicants = [self._to_build_applicant(row) for row in raw_applications]

        if not applicants:
            raise ValueError("신청자가 없습니다.")

        refresh_summary = await self.refresh_applications_before_build(applicants)

        refreshed_raw_applications = self.raid_application_repository.get_by_guild_channel_and_raid(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )
        applicants = [self._to_build_applicant(row) for row in refreshed_raw_applications]

        rule = self.party_rule_service.get_or_create_rule(
            guild_id=guild_id,
            channel_id=channel_id,
            raid_name=raid.raid_name,
        )

        plan = self.calculate_build_plan(len(applicants))
        parties = self.create_parties(plan, rule)
        applicants = self.sort_applicants(applicants)

        self.assign_priority_jobs(parties, applicants)
        self.assign_remaining_members(parties, applicants)

        waiting_members = [a for a in applicants if not a.is_assigned]

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
        summary = RefreshSummary()
        semaphore = asyncio.Semaphore(self.max_refresh_concurrency)
    
        async def refresh_one(applicant: BuildApplicant):
            async with semaphore:
                try:
                    latest_info = await asyncio.to_thread(
                        self.character_info_service.get_character_info,
                        applicant.character_name,
                        applicant.race,
                        applicant.server,
                    )
    
                    print(
                        f"[PARTY BUILD][REFRESH OK] "
                        f"character={applicant.character_name}, "
                        f"job={latest_info['job']}, "
                        f"item_level={latest_info['item_level']}, "
                        f"combat_power={latest_info['combat_power']}"
                    )
    
                    return {
                        "ok": True,
                        "character_name": applicant.character_name,
                        "application_id": applicant.application_id,
                        "job": latest_info["job"],
                        "item_level": latest_info["item_level"],
                        "combat_power": latest_info["combat_power"],
                    }
    
                except Exception as e:
                    print(
                        f"[PARTY BUILD][REFRESH FAIL] "
                        f"character={applicant.character_name}, "
                        f"race={applicant.race}, "
                        f"server={applicant.server}, "
                        f"error={repr(e)}"
                    )
                    return {
                        "ok": False,
                        "character_name": applicant.character_name,
                        "error": str(e),
                    }
    
        results = await asyncio.gather(*(refresh_one(a) for a in applicants))
    
        successful_updates: list[dict] = []
        failed_characters: list[str] = []
    
        for result in results:
            if result["ok"]:
                successful_updates.append(
                    {
                        "application_id": result["application_id"],
                        "job": result["job"],
                        "item_level": result["item_level"],
                        "combat_power": result["combat_power"],
                    }
                )
                summary.updated_count += 1
            else:
                failed_characters.append(result["character_name"])
                summary.failed_count += 1
                print(
                    f"[PARTY BUILD][REFRESH ERROR DETAIL] "
                    f"{result['character_name']}: {result['error']}"
                )
    
        updated_rows = self.raid_application_repository.bulk_update_character_snapshots(
            successful_updates
        )
    
        summary.failed_characters = failed_characters
    
        print(
            f"[PARTY BUILD][REFRESH SUMMARY] "
            f"updated={summary.updated_count}, "
            f"failed={summary.failed_count}, "
            f"db_updated_rows={updated_rows}, "
            f"failed_characters={summary.failed_characters}"
        )
    
        return summary

    def calculate_build_plan(self, total_count: int) -> BuildPlan:
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
        parties: list[BuildParty] = []

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

        if plan.temp_group_count == 1:
            temp_group_no = plan.full_group_count + 1
            temp_count = plan.temp_group_member_count

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
        return sorted(
            applicants,
            key=lambda a: (-a.combat_power, -a.item_level, a.application_id),
        )

    def assign_priority_jobs(
        self,
        parties: list[BuildParty],
        applicants: list[BuildApplicant],
    ) -> None:
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
    
        # 전투력 균형 최우선
        score -= self._power_balance_penalty(parties, target_party, candidate)
    
        # 같은 파티 동일 직업 최소화
        score -= self._job_duplicate_penalty(target_party, candidate)
    
        # 임시 공대 인원 균형 약하게 반영
        score -= self._temp_group_size_penalty(parties, target_party)
    
        # 미세 보정
        score += candidate.combat_power // 100
    
        return score

    def assign_remaining_members(
        self,
        parties: list[BuildParty],
        applicants: list[BuildApplicant],
    ) -> None:
        while True:
            available_parties = [party for party in parties if not party.is_full()]
            if not available_parties:
                break

            available_parties.sort(
                key=lambda p: (p.total_combat_power, len(p.members), p.group_no, p.party_no)
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
    
        # 1) 전체 전투력 균형 최우선
        score -= self._power_balance_penalty(parties, target_party, candidate)
    
        # 2) 우선 직업 미충족 보완
        if candidate.job in self.get_unfilled_priority_jobs(target_party):
            score += 120
    
        # 3) 선호 직업 보너스
        if candidate.job in target_party.preferred_jobs:
            score += 50
    
        # 4) 같은 파티 동일 직업 최소화
        score -= self._job_duplicate_penalty(target_party, candidate)
    
        # 5) 임시 공대 파티 인원 균형
        score -= self._temp_group_size_penalty(parties, target_party)
    
        # 6) 미세 보정
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

        self._validate_no_duplicate_users_in_groups(parties)
        
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
        return BuildApplicant(
            application_id=row.id,
            guild_id=row.guild_id,
            channel_id=row.channel_id,
            user_id=row.user_id,
            user_name=row.user_name,
            character_name=row.character_name,
            race=row.race,
            server=row.server,
            job=row.job,
            item_level=row.item_level,
            combat_power=row.combat_power,
            raid_name=row.raid_name,
        )

    def _all_party_powers_after_assignment(
        self,
        parties: list[BuildParty],
        target_party: BuildParty,
        candidate: BuildApplicant,
    ) -> list[int]:
        powers = []
        for party in parties:
            if party is target_party:
                powers.append(party.total_combat_power + candidate.combat_power)
            else:
                powers.append(party.total_combat_power)
        return powers
    
    
    def _power_balance_penalty(
        self,
        parties: list[BuildParty],
        target_party: BuildParty,
        candidate: BuildApplicant,
    ) -> int:
        powers = self._all_party_powers_after_assignment(parties, target_party, candidate)
        if not powers:
            return 0
    
        avg_power = sum(powers) / len(powers)
        penalty = sum(abs(power - avg_power) for power in powers)
        return int(penalty)
    
    
    def _job_duplicate_penalty(
        self,
        target_party: BuildParty,
        candidate: BuildApplicant,
    ) -> int:
        duplicate_count = sum(1 for member in target_party.members if member.job == candidate.job)
    
        if duplicate_count == 0:
            return 0
        if duplicate_count == 1:
            return 120
        if duplicate_count == 2:
            return 300
        return 600
    
    
    def _temp_group_size_penalty(
        self,
        parties: list[BuildParty],
        target_party: BuildParty,
    ) -> int:
        if not target_party.is_temp_group:
            return 0
    
        same_group_parties = [
            party for party in parties
            if party.group_no == target_party.group_no
        ]
    
        sizes = []
        for party in same_group_parties:
            if party is target_party:
                sizes.append(len(party.members) + 1)
            else:
                sizes.append(len(party.members))
    
        if not sizes:
            return 0
    
        return (max(sizes) - min(sizes)) * 80
    
    
    def _validate_no_duplicate_users_in_groups(
        self,
        parties: list[BuildParty],
    ) -> None:
        grouped_users: dict[int, set[int]] = {}
    
        for party in parties:
            grouped_users.setdefault(party.group_no, set())
    
            for member in party.members:
                if member.user_id in grouped_users[party.group_no]:
                    raise ValueError(
                        f"{party.group_no}공대에 동일한 유저 ID({member.user_id})가 중복 배치되었습니다."
                    )
                grouped_users[party.group_no].add(member.user_id)
