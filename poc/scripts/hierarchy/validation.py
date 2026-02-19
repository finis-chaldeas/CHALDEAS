"""
Temporal and spatial validation for event hierarchy.

Enforces constraints:
- Hard: ±50 years outside parent range = rejection
- Soft: Location mismatch = warning (recommendation only)
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


# Tolerance in years
TEMPORAL_TOLERANCE = 50  # ±50 years is allowed (boundary events)


class ValidationStatus(Enum):
    VALID = "valid"
    WARNING = "warning"
    REJECTED = "rejected"


@dataclass
class ValidationResult:
    status: ValidationStatus
    temporal_valid: bool
    temporal_warnings: list[str]
    spatial_warnings: list[str]
    score: float  # 0.0 - 1.0, higher is better

    @property
    def is_valid(self) -> bool:
        return self.status != ValidationStatus.REJECTED


def validate_temporal(
    child_start: int,
    child_end: Optional[int],
    parent_start: int,
    parent_end: Optional[int]
) -> tuple[bool, list[str]]:
    """
    Validate temporal containment.

    Returns:
        (is_valid, warnings)
        - is_valid: False if >50 years outside range (hard rejection)
        - warnings: List of soft warnings (boundary events)
    """
    child_end = child_end or child_start
    warnings = []

    # Hard limit: ±50 years outside parent range = rejection
    if child_start < parent_start - TEMPORAL_TOLERANCE:
        diff = parent_start - child_start
        return False, [f"시작일이 {diff}년 초과 벗어남 (허용: {TEMPORAL_TOLERANCE}년)"]

    if parent_end is not None:
        if child_end > parent_end + TEMPORAL_TOLERANCE:
            diff = child_end - parent_end
            return False, [f"종료일이 {diff}년 초과 벗어남 (허용: {TEMPORAL_TOLERANCE}년)"]

    # Soft warnings: boundary events (within tolerance but outside exact range)
    if child_start < parent_start:
        diff = parent_start - child_start
        warnings.append(f"시작일이 {diff}년 앞섬 (경계 이벤트)")

    if parent_end is not None and child_end > parent_end:
        diff = child_end - parent_end
        warnings.append(f"종료일이 {diff}년 뒤짐 (경계 이벤트)")

    return True, warnings


def validate_spatial(
    child_location: Optional[str],
    parent_locations: list[str]
) -> list[str]:
    """
    Validate spatial containment (soft, recommendation only).

    Some events (like World Wars) have no meaningful single location.

    Returns:
        List of warnings (empty if OK or not applicable)
    """
    if not child_location:
        return []  # Can't check

    if not parent_locations:
        return []  # Parent has no location constraints (e.g., World War)

    # Simple substring matching for now
    child_lower = child_location.lower()
    for parent_loc in parent_locations:
        if parent_loc.lower() in child_lower or child_lower in parent_loc.lower():
            return []  # Match found

    return [f"장소 불일치: '{child_location}' ∉ {parent_locations} (참고용)"]


def validate_hierarchy_level(parent_level: int, child_level: int) -> bool:
    """Validate hierarchy level order (parent must be lower number)."""
    return parent_level < child_level


def validate_parent_child(
    child_start: int,
    child_end: Optional[int],
    child_location: Optional[str],
    child_level: int,
    parent_start: int,
    parent_end: Optional[int],
    parent_locations: list[str],
    parent_level: int
) -> ValidationResult:
    """
    Full validation of parent-child relationship.

    Returns ValidationResult with status, warnings, and score.
    """
    # Level check (hard)
    if not validate_hierarchy_level(parent_level, child_level):
        return ValidationResult(
            status=ValidationStatus.REJECTED,
            temporal_valid=False,
            temporal_warnings=["계층 레벨 역전 (부모 level >= 자식 level)"],
            spatial_warnings=[],
            score=0.0
        )

    # Temporal check (hard for >50yr, soft for boundary)
    temporal_valid, temporal_warnings = validate_temporal(
        child_start, child_end, parent_start, parent_end
    )

    if not temporal_valid:
        return ValidationResult(
            status=ValidationStatus.REJECTED,
            temporal_valid=False,
            temporal_warnings=temporal_warnings,
            spatial_warnings=[],
            score=0.0
        )

    # Spatial check (soft, recommendation only)
    spatial_warnings = validate_spatial(child_location, parent_locations)

    # Calculate score
    score = 1.0
    if temporal_warnings:
        score -= 0.2 * len(temporal_warnings)
    if spatial_warnings:
        score -= 0.1 * len(spatial_warnings)  # Lower penalty for spatial

    score = max(0.0, score)

    # Determine status
    if temporal_warnings or spatial_warnings:
        status = ValidationStatus.WARNING
    else:
        status = ValidationStatus.VALID

    return ValidationResult(
        status=status,
        temporal_valid=True,
        temporal_warnings=temporal_warnings,
        spatial_warnings=spatial_warnings,
        score=score
    )


def can_be_parent(
    child_start: int,
    child_end: Optional[int],
    parent_start: int,
    parent_end: Optional[int],
    parent_level: int = 2,
    child_level: int = 3
) -> bool:
    """Quick check if parent is valid (hard constraints only)."""
    if parent_level >= child_level:
        return False

    temporal_valid, _ = validate_temporal(
        child_start, child_end, parent_start, parent_end
    )
    return temporal_valid


# Test
if __name__ == "__main__":
    print("Test 1: Valid relationship")
    result = validate_parent_child(
        child_start=1415, child_end=1415, child_location="Agincourt, France", child_level=3,
        parent_start=1337, parent_end=1453, parent_locations=["France", "England"], parent_level=2
    )
    print(f"  Status: {result.status.value}, Score: {result.score}")

    print("\nTest 2: Temporal rejection (>50yr outside)")
    result = validate_parent_child(
        child_start=1066, child_end=1066, child_location="Hastings", child_level=3,
        parent_start=1337, parent_end=1453, parent_locations=["France"], parent_level=2
    )
    print(f"  Status: {result.status.value}, Warnings: {result.temporal_warnings}")

    print("\nTest 3: Boundary event (within 50yr)")
    result = validate_parent_child(
        child_start=1320, child_end=1320, child_location="France", child_level=3,
        parent_start=1337, parent_end=1453, parent_locations=["France"], parent_level=2
    )
    print(f"  Status: {result.status.value}, Warnings: {result.temporal_warnings}")

    print("\nTest 4: Spatial warning")
    result = validate_parent_child(
        child_start=1415, child_end=1415, child_location="Germany", child_level=3,
        parent_start=1337, parent_end=1453, parent_locations=["France", "England"], parent_level=2
    )
    print(f"  Status: {result.status.value}, Spatial: {result.spatial_warnings}")
