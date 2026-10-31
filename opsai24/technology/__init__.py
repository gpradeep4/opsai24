"""Technology investigation plugin framework."""

from opsai24.technology.exceptions import (
    DuplicatePluginError,
    PluginRegistryError,
    UnsupportedProductError,
    UnsupportedVersionError,
)
from opsai24.technology.interfaces import TechnologyInvestigationPlugin
from opsai24.technology.mock_plugins import KubernetesMockPlugin, PostgreSQLMockPlugin
from opsai24.technology.models import InvestigationRequest, InvestigationResult
from opsai24.technology.registry import PluginRegistry

__all__ = [
    "DuplicatePluginError",
    "InvestigationRequest",
    "InvestigationResult",
    "KubernetesMockPlugin",
    "PluginRegistry",
    "PluginRegistryError",
    "PostgreSQLMockPlugin",
    "TechnologyInvestigationPlugin",
    "UnsupportedProductError",
    "UnsupportedVersionError",
]
