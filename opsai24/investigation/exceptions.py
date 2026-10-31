"""Typed errors for investigation lifecycle and persistence operations."""


class InvestigationError(Exception):
    """Base error for investigation workflows."""


class InvestigationNotFoundError(InvestigationError):
    """Raised when an investigation cannot be found."""


class InvalidStateTransitionError(InvestigationError):
    """Raised when a lifecycle transition is not allowed."""


class ConcurrencyConflictError(InvestigationError):
    """Raised when an update uses a stale revision."""


class InvestigationPersistenceError(InvestigationError):
    """Raised when persistence operations fail."""
