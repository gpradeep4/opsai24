"""Plugin registry for routing technology investigation requests."""

from opsai24.technology.exceptions import (
    DuplicatePluginError,
    UnsupportedProductError,
    UnsupportedVersionError,
)
from opsai24.technology.interfaces import TechnologyInvestigationPlugin
from opsai24.technology.models import InvestigationRequest, InvestigationResult


class PluginRegistry:
    """In-memory registry keyed by normalized product name."""

    def __init__(self) -> None:
        self._plugins: dict[str, TechnologyInvestigationPlugin] = {}

    @staticmethod
    def _normalize_product(product: str) -> str:
        return product.strip().lower()

    def register(self, plugin: TechnologyInvestigationPlugin) -> None:
        product_key = self._normalize_product(plugin.product)
        if product_key in self._plugins:
            raise DuplicatePluginError(f"Plugin already registered for '{plugin.product}'.")
        self._plugins[product_key] = plugin

    def list_products(self) -> list[str]:
        return sorted(plugin.product for plugin in self._plugins.values())

    def get_plugin(self, product: str) -> TechnologyInvestigationPlugin:
        product_key = self._normalize_product(product)
        if product_key not in self._plugins:
            raise UnsupportedProductError(f"No plugin registered for product '{product}'.")
        return self._plugins[product_key]

    def investigate(self, request: InvestigationRequest) -> InvestigationResult:
        plugin = self.get_plugin(request.product)
        if request.version not in plugin.supported_versions:
            raise UnsupportedVersionError(
                product=request.product,
                version=request.version,
                supported_versions=plugin.supported_versions,
            )
        return plugin.investigate(request)
