"""Stable interfaces for investigation plugins."""

from abc import ABC, abstractmethod

from opsai24.technology.models import InvestigationRequest, InvestigationResult


class TechnologyInvestigationPlugin(ABC):
    """Contract for product-specific technology investigation plugins."""

    product: str
    supported_versions: tuple[str, ...]

    @abstractmethod
    def investigate(self, request: InvestigationRequest) -> InvestigationResult:
        """Return a deterministic local investigation result for the request."""
