"""Reusable scenario definitions and machine-readable run summaries."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from opsai24.investigation.models import InvestigationState


class ScenarioOutcome(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"


def _parse_iso8601(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


@dataclass(frozen=True)
class ScenarioDefinition:
    """Input contract for one deterministic scenario run."""

    scenario_id: str
    incident_details: str
    affected_ci: str
    technology: str
    product_version: str
    window_start: str
    window_end: str
    fixture_refs: tuple[str, ...]
    expected_findings: tuple[str, ...]
    expected_component: str
    ai_conclusion_supported: bool = True

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id is required.")
        if _parse_iso8601(self.window_start) > _parse_iso8601(self.window_end):
            raise ValueError("window_start must be <= window_end.")
        if not self.fixture_refs:
            raise ValueError("fixture_refs cannot be empty.")
        if not self.expected_findings:
            raise ValueError("expected_findings cannot be empty.")


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    outcome: ScenarioOutcome
    investigation_id: str
    final_state: InvestigationState
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)
    missing_fixtures: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "outcome": self.outcome.value,
            "investigation_id": self.investigation_id,
            "final_state": self.final_state.value,
            "evidence_ids": list(self.evidence_ids),
            "missing_fixtures": list(self.missing_fixtures),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ScenarioRunSummary:
    results: tuple[ScenarioResult, ...]

    def to_dict(self) -> dict[str, Any]:
        passed = sum(result.outcome == ScenarioOutcome.PASSED for result in self.results)
        failed = sum(result.outcome == ScenarioOutcome.FAILED for result in self.results)
        incomplete = sum(result.outcome == ScenarioOutcome.INCOMPLETE for result in self.results)
        return {
            "passed": passed,
            "failed": failed,
            "incomplete": incomplete,
            "total": len(self.results),
            "scenarios": [result.to_dict() for result in self.results],
        }
