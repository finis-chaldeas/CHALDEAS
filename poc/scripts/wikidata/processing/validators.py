"""
검증기 - 데이터 완전성 검증

데이터 접근 없음. 순수 검증만.
"""

from typing import List, Tuple
from dataclasses import dataclass
from .transformers import Event, Location, Person


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    is_complete: bool
    issues: List[str]
    completeness_score: float  # 0.0 ~ 1.0


class EventValidator:
    """이벤트 완전성 검증"""

    # 완전한 이벤트에 필요한 필드 (가중치)
    REQUIRED_FIELDS = {
        'name': 1.0,          # 필수
        'start_year': 0.8,    # 거의 필수
        'locations': 0.7,     # 중요
        'description': 0.5,   # 권장
        'participants': 0.3,  # 선택
    }

    def validate(self, event: Event) -> ValidationResult:
        """이벤트 검증"""
        issues = []
        score = 0.0
        total_weight = sum(self.REQUIRED_FIELDS.values())

        # 이름 (필수)
        if event.name:
            score += self.REQUIRED_FIELDS['name']
        else:
            issues.append("이름 없음")

        # 날짜
        if event.start_year is not None:
            score += self.REQUIRED_FIELDS['start_year']
        else:
            issues.append("날짜 없음")

        # 위치
        if event.locations:
            # 위치 중 좌표 있는 것 비율로 점수
            with_coords = sum(1 for loc in event.locations if loc.latitude)
            loc_ratio = with_coords / len(event.locations) if event.locations else 0
            score += self.REQUIRED_FIELDS['locations'] * max(0.5, loc_ratio)
        else:
            issues.append("위치 없음")

        # 설명
        if event.description:
            score += self.REQUIRED_FIELDS['description']
        else:
            issues.append("설명 없음")

        # 참여자
        if event.participants:
            score += self.REQUIRED_FIELDS['participants']

        completeness = score / total_weight
        is_complete = completeness >= 0.8  # 80% 이상이면 완전
        is_valid = bool(event.name)  # 이름만 있으면 유효

        return ValidationResult(
            is_valid=is_valid,
            is_complete=is_complete,
            issues=issues,
            completeness_score=completeness
        )


class LocationValidator:
    """위치 완전성 검증"""

    def validate(self, location: Location) -> ValidationResult:
        """위치 검증"""
        issues = []
        score = 0.0

        if location.name:
            score += 0.4
        else:
            issues.append("이름 없음")

        if location.latitude is not None and location.longitude is not None:
            score += 0.5
        else:
            issues.append("좌표 없음")

        if location.location_type != 'unknown':
            score += 0.1

        return ValidationResult(
            is_valid=bool(location.name),
            is_complete=score >= 0.8,
            issues=issues,
            completeness_score=score
        )


class BatchValidator:
    """배치 검증"""

    def __init__(self):
        self.event_validator = EventValidator()
        self.location_validator = LocationValidator()

    def validate_events(self, events: List[Event]) -> dict:
        """이벤트 배치 검증"""
        total = len(events)
        valid = 0
        complete = 0
        total_score = 0.0

        issue_counts = {}

        for event in events:
            result = self.event_validator.validate(event)

            if result.is_valid:
                valid += 1
            if result.is_complete:
                complete += 1
            total_score += result.completeness_score

            for issue in result.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        return {
            'total': total,
            'valid': valid,
            'valid_pct': 100 * valid / total if total else 0,
            'complete': complete,
            'complete_pct': 100 * complete / total if total else 0,
            'avg_completeness': total_score / total if total else 0,
            'issues': issue_counts
        }
