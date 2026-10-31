"""Investigation models and lifecycle validation."""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from opsai24.investigation.exceptions import InvalidStateTransitionError


class InvestigationState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = {
    InvestigationState.COMPLETED,
    InvestigationState.PARTIAL,
    InvestigationState.FAILED,
    InvestigationState.CANCELLED,
}

ALLOWED_TRANSITIONS: dict[InvestigationState, set[InvestigationState]] = {
    InvestigationState.QUEUED: {InvestigationState.RUNNING, InvestigationState.CANCELLED},
    InvestigationState.RUNNING: {
        InvestigationState.COMPLETED,
        InvestigationState.PARTIAL,
        InvestigationState.FAILED,
        InvestigationState.CANCELLED,
    },
    InvestigationState.COMPLETED: set(),
    InvestigationState.PARTIAL: set(),
    InvestigationState.FAILED: set(),
    InvestigationState.CANCELLED: set(),
}


def utcnow_iso() -> str:
    """Return an RFC3339-like UTC timestamp with second precision."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def validate_transition(current: InvestigationState, next_state: InvestigationState) -> None:
    """Ensure a lifecycle transition is legal."""
    if next_state == current:
        return

    if current in TERMINAL_STATES and next_state == InvestigationState.RUNNING:
        raise InvalidStateTransitionError(
            f"Cannot transition from terminal state '{current}' back to RUNNING."
        )

    allowed = ALLOWED_TRANSITIONS[current]
    if next_state not in allowed:
        allowed_names = ", ".join(state.value for state in sorted(allowed))
        raise InvalidStateTransitionError(
            f"Invalid transition {current.value} -> {next_state.value}. "
            f"Allowed: {allowed_names or 'none'}."
        )


@dataclass(frozen=True)
class Investigation:
    """Persisted investigation lifecycle record."""

    investigation_id: str
    source_event_id: str
    product: str
    version: str
    state: InvestigationState = InvestigationState.QUEUED
    progress_percent: int = 0
    status_message: str = ""
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    error_summary: str | None = None
    revision: int = 0
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)

    def with_updates(self, **changes: Any) -> "Investigation":
        """Create a revised copy, typically prior to persistence update."""
        return replace(self, **changes)
