"""Fixture evidence adapters for deterministic scenario runs."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FixtureEvidence:
    evidence_id: str
    fixture_ref: str
    observed_at: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def observed_at_datetime(self) -> datetime:
        return datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))


class EvidenceFixtureAdapter(ABC):
    @abstractmethod
    def load(self, fixture_ref: str) -> FixtureEvidence | None:
        """Resolve fixture evidence by reference."""


class FileFixtureAdapter(EvidenceFixtureAdapter):
    """Local filesystem adapter used by tests."""

    def __init__(self, fixture_root: str, observed_at_by_ref: dict[str, str]) -> None:
        self._root = Path(fixture_root)
        self._observed_at_by_ref = observed_at_by_ref

    def load(self, fixture_ref: str) -> FixtureEvidence | None:
        fixture_path = self._root / fixture_ref
        if not fixture_path.exists():
            return None

        observed_at = self._observed_at_by_ref.get(fixture_ref)
        if observed_at is None:
            return None

        content = fixture_path.read_text(encoding="utf-8")
        evidence_id = f"evidence-{fixture_ref.replace('/', '-').replace('.', '-')}"
        return FixtureEvidence(
            evidence_id=evidence_id,
            fixture_ref=fixture_ref,
            observed_at=observed_at,
            content=content,
            metadata={"source": "synthetic-log-fixture"},
        )
