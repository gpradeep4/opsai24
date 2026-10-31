import unittest

from opsai24.investigation import (
    ConcurrencyConflictError,
    InMemoryInvestigationStore,
    InvestigationPersistenceError,
    InvestigationService,
    InvestigationState,
    InvalidStateTransitionError,
)


class FailingStore(InMemoryInvestigationStore):
    def __init__(self, *, fail_on_save: bool = False, fail_on_update: bool = False) -> None:
        super().__init__()
        self.fail_on_save = fail_on_save
        self.fail_on_update = fail_on_update

    def save_new(self, investigation):
        if self.fail_on_save:
            raise RuntimeError("backend token failed")
        return super().save_new(investigation)

    def update(self, investigation, expected_revision):
        if self.fail_on_update:
            raise RuntimeError("db password mismatch")
        return super().update(investigation, expected_revision)


class InvestigationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryInvestigationStore()
        self.service = InvestigationService(self.store)

    def test_create_investigation(self) -> None:
        investigation = self.service.create_investigation(
            source_event_id="evt-123",
            product="kubernetes",
            version="1.29",
            evidence_ids=["ev-1", "ev-1", " ev-2 "],
            metadata={"region": "us-west", "api_token": "secret-value"},
        )
        self.assertEqual(investigation.state, InvestigationState.CREATED)
        self.assertEqual(investigation.source_event_id, "evt-123")
        self.assertEqual(investigation.evidence_ids, ("ev-1", "ev-2"))
        self.assertNotIn("api_token", investigation.metadata)

    def test_valid_lifecycle_transitions(self) -> None:
        created = self.service.create_investigation(
            source_event_id="evt-234",
            product="postgresql",
            version="16",
        )
        running = self.service.transition_state(
            investigation_id=created.investigation_id,
            next_state=InvestigationState.RUNNING,
            expected_revision=0,
            status_message="running checks",
        )
        self.assertEqual(running.state, InvestigationState.RUNNING)
        self.assertEqual(running.revision, 1)

        succeeded = self.service.transition_state(
            investigation_id=running.investigation_id,
            next_state=InvestigationState.SUCCEEDED,
            expected_revision=1,
        )
        self.assertEqual(succeeded.state, InvestigationState.SUCCEEDED)
        self.assertEqual(succeeded.progress_percent, 100)

    def test_invalid_transition_and_no_regression_to_running(self) -> None:
        created = self.service.create_investigation(
            source_event_id="evt-345",
            product="postgresql",
            version="16",
        )
        with self.assertRaises(InvalidStateTransitionError):
            self.service.transition_state(
                investigation_id=created.investigation_id,
                next_state=InvestigationState.SUCCEEDED,
                expected_revision=0,
            )

        failed = self.service.transition_state(
            investigation_id=created.investigation_id,
            next_state=InvestigationState.RUNNING,
            expected_revision=0,
        )
        failed = self.service.transition_state(
            investigation_id=failed.investigation_id,
            next_state=InvestigationState.FAILED,
            expected_revision=1,
            error_message="api_key leaked",
        )
        self.assertEqual(failed.error_summary, "[REDACTED]")
        with self.assertRaises(InvalidStateTransitionError):
            self.service.transition_state(
                investigation_id=failed.investigation_id,
                next_state=InvestigationState.RUNNING,
                expected_revision=2,
            )

    def test_idempotency_for_duplicate_source_event(self) -> None:
        first = self.service.create_investigation(
            source_event_id="evt-same",
            product="kubernetes",
            version="1.29",
        )
        second = self.service.create_investigation(
            source_event_id="evt-same",
            product="postgresql",
            version="16",
        )
        self.assertEqual(second.investigation_id, first.investigation_id)
        self.assertEqual(second.product, "kubernetes")

    def test_concurrent_state_change_conflict(self) -> None:
        created = self.service.create_investigation(
            source_event_id="evt-456",
            product="postgresql",
            version="16",
        )
        self.service.transition_state(
            investigation_id=created.investigation_id,
            next_state=InvestigationState.RUNNING,
            expected_revision=0,
        )
        with self.assertRaises(ConcurrencyConflictError):
            self.service.transition_state(
                investigation_id=created.investigation_id,
                next_state=InvestigationState.SUCCEEDED,
                expected_revision=0,
            )

    def test_persistence_failure_is_sanitized(self) -> None:
        service = InvestigationService(FailingStore(fail_on_save=True))
        with self.assertRaises(InvestigationPersistenceError) as error_context:
            service.create_investigation(
                source_event_id="evt-567",
                product="kubernetes",
                version="1.29",
            )
        self.assertEqual(str(error_context.exception), "[REDACTED]")

        failing_update_service = InvestigationService(FailingStore(fail_on_update=True))
        created = failing_update_service.create_investigation(
            source_event_id="evt-678",
            product="kubernetes",
            version="1.29",
        )
        with self.assertRaises(InvestigationPersistenceError) as update_error:
            failing_update_service.transition_state(
                investigation_id=created.investigation_id,
                next_state=InvestigationState.RUNNING,
                expected_revision=0,
            )
        self.assertEqual(str(update_error.exception), "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
