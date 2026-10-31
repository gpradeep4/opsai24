import json
from pathlib import Path
import unittest

from opsai24.investigation import InMemoryInvestigationStore, InvestigationService, InvestigationState
from opsai24.scenarios import (
    FileFixtureAdapter,
    INITIAL_SCENARIOS,
    ScenarioDefinition,
    ScenarioOutcome,
    ScenarioRunner,
)
from opsai24.technology import KubernetesMockPlugin, PluginRegistry, PostgreSQLMockPlugin


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "scenarios"


OBSERVED_AT_BY_REF = {
    "linux-disk-warning.log": "2026-10-01T10:05:12Z",
    "linux-cpu-warning.log": "2026-10-01T11:05:52Z",
    "weblogic-deploy-failure.log": "2026-10-01T12:10:01Z",
    "tomcat-exception.log": "2026-10-01T13:08:45Z",
    "mongodb-connection-failure.log": "2026-10-01T14:10:11Z",
    "postgresql-connection-issue.log": "2026-10-01T15:10:45Z",
    "app-db-connectivity-failure.log": "2026-10-01T16:15:03Z",
}


class ScenarioRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = InvestigationService(InMemoryInvestigationStore())
        self.adapter = FileFixtureAdapter(str(FIXTURE_ROOT), OBSERVED_AT_BY_REF)
        registry = PluginRegistry()
        registry.register(KubernetesMockPlugin())
        registry.register(PostgreSQLMockPlugin())
        self.registry = registry
        self.runner = ScenarioRunner(
            investigation_service=self.service,
            fixture_adapter=self.adapter,
            plugin_registry=self.registry,
        )

    def test_initial_scenarios_include_required_definitions(self) -> None:
        ids = {scenario.scenario_id for scenario in INITIAL_SCENARIOS}
        self.assertEqual(
            ids,
            {
                "linux-disk-space-warning",
                "linux-cpu-warning",
                "weblogic-deployment-failure",
                "tomcat-application-exception",
                "mongodb-connection-failure",
                "postgresql-connection-issue",
                "app-to-db-connectivity-failure",
            },
        )

    def test_successful_scenario_validates_mapping_and_evidence(self) -> None:
        scenario = INITIAL_SCENARIOS[0]
        result = self.runner.run_one(scenario)
        self.assertEqual(result.outcome, ScenarioOutcome.PASSED)
        self.assertEqual(result.final_state, InvestigationState.COMPLETED)
        self.assertTrue(result.evidence_ids)

        status = self.service.get_status(result.investigation_id)
        self.assertEqual(status.state, InvestigationState.COMPLETED)
        self.assertEqual(status.progress_percent, 100)
        self.assertEqual(status.product, "kubernetes")

    def test_unsupported_technology_returns_partial_incomplete(self) -> None:
        unsupported = next(
            scenario
            for scenario in INITIAL_SCENARIOS
            if scenario.scenario_id == "weblogic-deployment-failure"
        )
        result = self.runner.run_one(unsupported)
        self.assertEqual(result.outcome, ScenarioOutcome.INCOMPLETE)
        self.assertEqual(result.final_state, InvestigationState.PARTIAL)
        self.assertIn("unsupported technology handling", result.notes)

    def test_missing_evidence_returns_partial(self) -> None:
        missing_fixture_scenario = ScenarioDefinition(
            scenario_id="missing-evidence",
            incident_details="Fixture missing in adapter.",
            affected_ci="ci-test-missing-01",
            technology="kubernetes",
            product_version="1.29",
            window_start="2026-10-01T10:00:00Z",
            window_end="2026-10-01T10:30:00Z",
            fixture_refs=("does-not-exist.log",),
            expected_findings=("disk",),
            expected_component="infrastructure",
        )
        result = self.runner.run_one(missing_fixture_scenario)
        self.assertEqual(result.outcome, ScenarioOutcome.INCOMPLETE)
        self.assertEqual(result.final_state, InvestigationState.PARTIAL)
        self.assertEqual(result.missing_fixtures, ("does-not-exist.log",))

    def test_timestamp_window_handling(self) -> None:
        adapter = FileFixtureAdapter(
            str(FIXTURE_ROOT),
            {
                **OBSERVED_AT_BY_REF,
                "linux-disk-warning.log": "2026-10-01T09:00:00Z",
            },
        )
        runner = ScenarioRunner(
            investigation_service=InvestigationService(InMemoryInvestigationStore()),
            fixture_adapter=adapter,
            plugin_registry=self.registry,
        )
        result = runner.run_one(INITIAL_SCENARIOS[0])
        self.assertEqual(result.outcome, ScenarioOutcome.FAILED)
        self.assertEqual(result.final_state, InvestigationState.FAILED)
        self.assertIn("timestamp outside event window", result.notes)

    def test_expected_evidence_identification_failure(self) -> None:
        scenario = ScenarioDefinition(
            scenario_id="missing-finding-token",
            incident_details="Finding token does not exist in fixture text.",
            affected_ci="ci-test-findings-01",
            technology="kubernetes",
            product_version="1.29",
            window_start="2026-10-01T10:00:00Z",
            window_end="2026-10-01T10:30:00Z",
            fixture_refs=("linux-disk-warning.log",),
            expected_findings=("nonexistent-token",),
            expected_component="infrastructure",
        )
        result = self.runner.run_one(scenario)
        self.assertEqual(result.outcome, ScenarioOutcome.FAILED)
        self.assertEqual(result.final_state, InvestigationState.FAILED)
        self.assertIn("expected evidence identification failed", result.notes)

    def test_incident_component_mapping_mismatch(self) -> None:
        scenario = ScenarioDefinition(
            scenario_id="wrong-component-map",
            incident_details="Technology mapping intentionally wrong.",
            affected_ci="ci-test-mapping-01",
            technology="kubernetes",
            product_version="1.29",
            window_start="2026-10-01T10:00:00Z",
            window_end="2026-10-01T10:30:00Z",
            fixture_refs=("linux-disk-warning.log",),
            expected_findings=("disk",),
            expected_component="database",
        )
        result = self.runner.run_one(scenario)
        self.assertEqual(result.outcome, ScenarioOutcome.FAILED)
        self.assertEqual(result.final_state, InvestigationState.FAILED)

    def test_unsupported_ai_conclusion_returns_partial(self) -> None:
        scenario = ScenarioDefinition(
            scenario_id="unsupported-ai-conclusion",
            incident_details="AI result unsupported for this deterministic run.",
            affected_ci="ci-ai-conclusion-01",
            technology="kubernetes",
            product_version="1.29",
            window_start="2026-10-01T10:00:00Z",
            window_end="2026-10-01T10:30:00Z",
            fixture_refs=("linux-disk-warning.log",),
            expected_findings=("disk utilization",),
            expected_component="infrastructure",
            ai_conclusion_supported=False,
        )
        result = self.runner.run_one(scenario)
        self.assertEqual(result.outcome, ScenarioOutcome.INCOMPLETE)
        self.assertEqual(result.final_state, InvestigationState.PARTIAL)
        self.assertIn("unsupported AI conclusions", result.notes)

    def test_machine_readable_summary(self) -> None:
        selected = (
            INITIAL_SCENARIOS[0],  # expected pass
            INITIAL_SCENARIOS[2],  # unsupported technology -> incomplete
        )
        summary = self.runner.run(selected).to_dict()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["incomplete"], 1)
        self.assertEqual(summary["failed"], 0)
        # Ensure downstream systems can consume JSON directly.
        json.dumps(summary)


if __name__ == "__main__":
    unittest.main()
