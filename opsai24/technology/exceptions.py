"""Typed exceptions for registry and compatibility errors."""


class PluginRegistryError(Exception):
    """Base exception for plugin-registry errors."""


class DuplicatePluginError(PluginRegistryError):
    """Raised when attempting to register the same product twice."""


class UnsupportedProductError(PluginRegistryError):
    """Raised when no plugin exists for a requested product."""


class UnsupportedVersionError(PluginRegistryError):
    """Raised when a plugin exists, but not for the requested version."""

    def __init__(self, product: str, version: str, supported_versions: tuple[str, ...]):
        message = (
            f"Unsupported version '{version}' for product '{product}'. "
            f"Supported versions: {', '.join(supported_versions)}"
        )
        super().__init__(message)
        self.product = product
        self.version = version
        self.supported_versions = supported_versions
