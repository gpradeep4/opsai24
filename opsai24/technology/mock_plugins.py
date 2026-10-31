"""Local mock plugins used for framework development and tests."""

from opsai24.technology.interfaces import TechnologyInvestigationPlugin
from opsai24.technology.models import InvestigationRequest, InvestigationResult


class KubernetesMockPlugin(TechnologyInvestigationPlugin):
    product = "kubernetes"
    supported_versions = ("1.28", "1.29")

    def investigate(self, request: InvestigationRequest) -> InvestigationResult:
        return InvestigationResult(
            product=request.product,
            version=request.version,
            summary="Mock Kubernetes investigation completed.",
            findings={
                "cluster_health": "green",
                "control_plane_latency_ms": 22,
                "notes": "Mock data only; no remote calls were executed.",
            },
        )


class PostgreSQLMockPlugin(TechnologyInvestigationPlugin):
    product = "postgresql"
    supported_versions = ("15", "16")

    def investigate(self, request: InvestigationRequest) -> InvestigationResult:
        return InvestigationResult(
            product=request.product,
            version=request.version,
            summary="Mock PostgreSQL investigation completed.",
            findings={
                "replication_lag_seconds": 0,
                "index_bloat_risk": "low",
                "notes": "Mock data only; no remote calls were executed.",
            },
        )
