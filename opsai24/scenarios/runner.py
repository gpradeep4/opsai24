"""Scenario runner built on InvestigationService."""

from datetime import datetime

from opsai24.investigation.models import InvestigationState
from opsai24.investigation.service import InvestigationService
from opsai24.scenarios.adapters import EvidenceFixtureAdapter
from opsai24.scenarios.models import (
    ScenarioDefinition,
    ScenarioOutcome,
    ScenarioResult,
    ScenarioRunSummary,
)
from opsai24.technology import InvestigationRequest, PluginRegistry
from opsai24.technology.exceptions import UnsupportedProductError, UnsupportedVersionError

TECHNOLOGY_COMPONENT_MAP: dict[str, str] = {
    "kubernetes": "infrastructure",
    "weblogic": "application",
    "tomcat": "application",
    "mongodb": "database",
    "postgresql": "database",
    "service-connectivity": "network",
}


def _parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ScenarioRunner:
    """Runs deterministic scenarios and returns machine-readable results."""

    def __init__(
        self,
        *,
        investigation_service: InvestigationService,
        fixture_adapter: EvidenceFixtureAdapter,
        plugin_registry: PluginRegistry,
    ) -> None:
        self._investigation_service = investigation_service
        self._fixture_adapter = fixture_adapter
        self._plugin_registry = plugin_registry

    def run(self, scenarios: tuple[ScenarioDefinition, ...]) -> ScenarioRunSummary:
        results = tuple(self.run_one(scenario) for scenario in scenarios)
        return ScenarioRunSummary(results=results)

    def run_one(self, scenario: ScenarioDefinition) -> ScenarioResult:
        investigation = self._investigation_service.create_investigation(
            source_event_id=f"scenario:{scenario.scenario_id}",
            product=scenario.technology,
            version=scenario.product_version,
            metadata={"affected_ci": scenario.affected_ci, "incident": scenario.incident_details},
        )
        investigation = self._investigation_service.transition_state(
            investigation_id=investigation.investigation_id,
            next_state=InvestigationState.RUNNING,
            expected_revision=investigation.revision,
            status_message="scenario started",
        )

        mapped_component = TECHNOLOGY_COMPONENT_MAP.get(scenario.technology)
        if mapped_component != scenario.expected_component:
            final = self._investigation_service.transition_state(
                investigation_id=investigation.investigation_id,
                next_state=InvestigationState.FAILED,
                expected_revision=investigation.revision,
                error_message="component mapping mismatch",
            )
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                outcome=ScenarioOutcome.FAILED,
                investigation_id=final.investigation_id,
                final_state=final.state,
                notes=("incident/component mapping mismatch",),
            )

        try:
            self._plugin_registry.investigate(
                InvestigationRequest(
                    product=scenario.technology,
                    version=scenario.product_version,
                    context={"scenario_id": scenario.scenario_id},
                )
            )
        except (UnsupportedProductError, UnsupportedVersionError):
            final = self._investigation_service.transition_state(
                investigation_id=investigation.investigation_id,
                next_state=InvestigationState.PARTIAL,
                expected_revision=investigation.revision,
                status_message="unsupported technology/version",
            )
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                outcome=ScenarioOutcome.INCOMPLETE,
                investigation_id=final.investigation_id,
                final_state=final.state,
                notes=("unsupported technology handling",),
            )

        evidence_ids: list[str] = []
        missing_fixtures: list[str] = []
        note_set: set[str] = set()
        expected_start = _parse_iso8601(scenario.window_start)
        expected_end = _parse_iso8601(scenario.window_end)
        corpus = ""

        for fixture_ref in scenario.fixture_refs:
            evidence = self._fixture_adapter.load(fixture_ref)
            if evidence is None:
                missing_fixtures.append(fixture_ref)
                continue

            observed = evidence.observed_at_datetime()
            if not (expected_start <= observed <= expected_end):
                note_set.add("timestamp outside event window")
                continue

            evidence_ids.append(evidence.evidence_id)
            corpus = f"{corpus}\n{evidence.content}".lower()

        if missing_fixtures:
            final = self._investigation_service.transition_state(
                investigation_id=investigation.investigation_id,
                next_state=InvestigationState.PARTIAL,
                expected_revision=investigation.revision,
                status_message="missing evidence fixtures",
            )
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                outcome=ScenarioOutcome.INCOMPLETE,
                investigation_id=final.investigation_id,
                final_state=final.state,
                evidence_ids=tuple(evidence_ids),
                missing_fixtures=tuple(missing_fixtures),
                notes=tuple(sorted(note_set.union({"missing evidence"}))),
            )

        missing_findings = [
            finding for finding in scenario.expected_findings if finding.lower() not in corpus
        ]
        if missing_findings:
            final = self._investigation_service.transition_state(
                investigation_id=investigation.investigation_id,
                next_state=InvestigationState.FAILED,
                expected_revision=investigation.revision,
                error_message="expected evidence not identified",
            )
            note_set.add("expected evidence identification failed")
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                outcome=ScenarioOutcome.FAILED,
                investigation_id=final.investigation_id,
                final_state=final.state,
                evidence_ids=tuple(evidence_ids),
                notes=tuple(sorted(note_set)),
            )

        if not scenario.ai_conclusion_supported:
            final = self._investigation_service.transition_state(
                investigation_id=investigation.investigation_id,
                next_state=InvestigationState.PARTIAL,
                expected_revision=investigation.revision,
                status_message="unsupported AI conclusions",
            )
            note_set.add("unsupported AI conclusions")
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                outcome=ScenarioOutcome.INCOMPLETE,
                investigation_id=final.investigation_id,
                final_state=final.state,
                evidence_ids=tuple(evidence_ids),
                notes=tuple(sorted(note_set)),
            )

        final = self._investigation_service.transition_state(
            investigation_id=investigation.investigation_id,
            next_state=InvestigationState.COMPLETED,
            expected_revision=investigation.revision,
            status_message="scenario completed",
        )
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            outcome=ScenarioOutcome.PASSED,
            investigation_id=final.investigation_id,
            final_state=final.state,
            evidence_ids=tuple(evidence_ids),
            notes=tuple(sorted(note_set)),
        )
