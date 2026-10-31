"""Stable data models for technology investigation plugins."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InvestigationRequest:
    """Input envelope provided to a technology investigation plugin."""

    product: str
    version: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InvestigationResult:
    """Normalized investigation result returned by plugins."""

    product: str
    version: str
    summary: str
    findings: dict[str, Any] = field(default_factory=dict)
