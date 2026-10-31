"""Framework-independent investigation lifecycle service."""

from uuid import uuid4

from opsai24.investigation.exceptions import (
    ConcurrencyConflictError,
    InvestigationNotFoundError,
    InvestigationPersistenceError,
)
from opsai24.investigation.models import (
    Investigation,
    InvestigationState,
    TERMINAL_STATES,
    utcnow_iso,
    validate_transition,
)
from opsai24.investigation.persistence import InvestigationStore

SECRET_FIELD_MARKERS = ("secret", "token", "password", "credential", "api_key", "key")


def _contains_secret_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in SECRET_FIELD_MARKERS)


def _sanitize_text(value: str | None) -> str | None:
    if value is None:
        return None
    if _contains_secret_marker(value):
        return "[REDACTED]"
    return value


def _sanitize_metadata(metadata: dict[str, object] | None) -> dict[str, object]:
    if not metadata:
        return {}

    sanitized: dict[str, object] = {}
    for key, value in metadata.items():
        if _contains_secret_marker(key):
            continue

        if isinstance(value, dict):
            nested = _sanitize_metadata(value)
            sanitized[key] = nested
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_metadata(item) if isinstance(item, dict) else item for item in value
            ]
        elif isinstance(value, str):
            sanitized[key] = _sanitize_text(value) or ""
        else:
            sanitized[key] = value

    return sanitized


def _normalize_evidence_ids(evidence_ids: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if evidence_ids is None:
        return ()

    normalized: list[str] = []
    for evidence_id in evidence_ids:
        if not isinstance(evidence_id, str):
            raise ValueError("Evidence must be referenced by ID string only.")
        clean_id = evidence_id.strip()
        if clean_id:
            normalized.append(clean_id)

    # Preserve caller order while removing duplicates.
    deduplicated: list[str] = []
    seen: set[str] = set()
    for evidence_id in normalized:
        if evidence_id not in seen:
            deduplicated.append(evidence_id)
            seen.add(evidence_id)
    return tuple(deduplicated)


class InvestigationService:
    """Lifecycle service independent of plugin implementation details."""

    def __init__(self, store: InvestigationStore) -> None:
        self._store = store

    def create_investigation(
        self,
        *,
        source_event_id: str,
        product: str,
        version: str,
        evidence_ids: list[str] | tuple[str, ...] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Investigation:
        event_id = source_event_id.strip()
        if not event_id:
            raise ValueError("source_event_id is required.")

        existing = self._store.get_by_source_event_id(event_id)
        if existing is not None:
            return existing

        investigation = Investigation(
            investigation_id=f"inv-{uuid4().hex[:12]}",
            source_event_id=event_id,
            product=product.strip().lower(),
            version=version.strip(),
            state=InvestigationState.CREATED,
            progress_percent=0,
            evidence_ids=_normalize_evidence_ids(evidence_ids),
            metadata=_sanitize_metadata(metadata),
        )
        try:
            return self._store.save_new(investigation)
        except Exception as error:  # pragma: no cover - tested via fake failing store.
            safe_error = _sanitize_text(str(error)) or "Persistence failure."
            raise InvestigationPersistenceError(safe_error) from error

    def transition_state(
        self,
        *,
        investigation_id: str,
        next_state: InvestigationState,
        expected_revision: int,
        status_message: str | None = None,
        error_message: str | None = None,
        progress_percent: int | None = None,
    ) -> Investigation:
        current = self.get_status(investigation_id)
        validate_transition(current.state, next_state)

        if progress_percent is None:
            progress = 100 if next_state in TERMINAL_STATES else current.progress_percent
        else:
            progress = self._validate_progress(progress_percent)

        updated = current.with_updates(
            state=next_state,
            progress_percent=progress,
            status_message=_sanitize_text(status_message) or current.status_message,
            error_summary=_sanitize_text(error_message)
            if next_state == InvestigationState.FAILED
            else None,
            updated_at=utcnow_iso(),
            revision=current.revision + 1,
        )
        try:
            return self._store.update(updated, expected_revision=expected_revision)
        except ConcurrencyConflictError:
            raise
        except Exception as error:  # pragma: no cover - tested via fake failing store.
            safe_error = _sanitize_text(str(error)) or "Persistence failure."
            raise InvestigationPersistenceError(safe_error) from error

    def update_progress(
        self,
        *,
        investigation_id: str,
        progress_percent: int,
        expected_revision: int,
        status_message: str | None = None,
    ) -> Investigation:
        current = self.get_status(investigation_id)
        if current.state in TERMINAL_STATES:
            raise ValueError("Cannot update progress for a completed investigation.")

        updated = current.with_updates(
            progress_percent=self._validate_progress(progress_percent),
            status_message=_sanitize_text(status_message) or current.status_message,
            updated_at=utcnow_iso(),
            revision=current.revision + 1,
        )
        try:
            return self._store.update(updated, expected_revision=expected_revision)
        except ConcurrencyConflictError:
            raise
        except Exception as error:  # pragma: no cover - tested via fake failing store.
            safe_error = _sanitize_text(str(error)) or "Persistence failure."
            raise InvestigationPersistenceError(safe_error) from error

    def get_status(self, investigation_id: str) -> Investigation:
        investigation = self._store.get_by_id(investigation_id)
        if investigation is None:
            raise InvestigationNotFoundError(
                f"Investigation '{investigation_id}' could not be found."
            )
        return investigation

    @staticmethod
    def _validate_progress(progress_percent: int) -> int:
        if not 0 <= progress_percent <= 100:
            raise ValueError("progress_percent must be between 0 and 100.")
        return progress_percent
