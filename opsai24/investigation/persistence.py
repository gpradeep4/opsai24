"""Persistence abstraction and local in-memory adapter."""

from abc import ABC, abstractmethod

from opsai24.investigation.exceptions import ConcurrencyConflictError
from opsai24.investigation.models import Investigation


class InvestigationStore(ABC):
    """Storage contract used by InvestigationService."""

    @abstractmethod
    def save_new(self, investigation: Investigation) -> Investigation:
        """Persist a newly-created investigation."""

    @abstractmethod
    def get_by_id(self, investigation_id: str) -> Investigation | None:
        """Look up an investigation by primary ID."""

    @abstractmethod
    def get_by_source_event_id(self, source_event_id: str) -> Investigation | None:
        """Look up an investigation by source event ID."""

    @abstractmethod
    def update(self, investigation: Investigation, expected_revision: int) -> Investigation:
        """Persist an updated investigation with optimistic concurrency."""


class InMemoryInvestigationStore(InvestigationStore):
    """Small local adapter suitable for tests and local development."""

    def __init__(self) -> None:
        self._by_id: dict[str, Investigation] = {}
        self._id_by_source_event: dict[str, str] = {}

    def save_new(self, investigation: Investigation) -> Investigation:
        if investigation.investigation_id in self._by_id:
            raise ConcurrencyConflictError(
                f"Investigation '{investigation.investigation_id}' already exists."
            )
        if investigation.source_event_id in self._id_by_source_event:
            existing_id = self._id_by_source_event[investigation.source_event_id]
            return self._by_id[existing_id]

        self._by_id[investigation.investigation_id] = investigation
        self._id_by_source_event[investigation.source_event_id] = investigation.investigation_id
        return investigation

    def get_by_id(self, investigation_id: str) -> Investigation | None:
        return self._by_id.get(investigation_id)

    def get_by_source_event_id(self, source_event_id: str) -> Investigation | None:
        existing_id = self._id_by_source_event.get(source_event_id)
        if existing_id is None:
            return None
        return self._by_id[existing_id]

    def update(self, investigation: Investigation, expected_revision: int) -> Investigation:
        current = self._by_id.get(investigation.investigation_id)
        if current is None:
            raise ConcurrencyConflictError(
                f"Investigation '{investigation.investigation_id}' no longer exists."
            )
        if current.revision != expected_revision:
            raise ConcurrencyConflictError(
                f"Revision conflict for '{investigation.investigation_id}': "
                f"expected {expected_revision}, got {current.revision}."
            )

        self._by_id[investigation.investigation_id] = investigation
        self._id_by_source_event[investigation.source_event_id] = investigation.investigation_id
        return investigation
