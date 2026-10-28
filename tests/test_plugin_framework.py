import unittest

from opsai24.technology import (
    DuplicatePluginError,
    InvestigationRequest,
    KubernetesMockPlugin,
    PluginRegistry,
    PostgreSQLMockPlugin,
    UnsupportedProductError,
    UnsupportedVersionError,
)


class PluginFrameworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = PluginRegistry()
        self.registry.register(KubernetesMockPlugin())
        self.registry.register(PostgreSQLMockPlugin())

    def test_lists_registered_products(self) -> None:
        self.assertEqual(self.registry.list_products(), ["kubernetes", "postgresql"])

    def test_rejects_duplicate_registration(self) -> None:
        with self.assertRaises(DuplicatePluginError):
            self.registry.register(KubernetesMockPlugin())

    def test_raises_for_unsupported_product(self) -> None:
        with self.assertRaises(UnsupportedProductError):
            self.registry.investigate(InvestigationRequest(product="redis", version="7"))

    def test_raises_for_unsupported_version(self) -> None:
        with self.assertRaises(UnsupportedVersionError) as error_context:
            self.registry.investigate(
                InvestigationRequest(product="kubernetes", version="1.30")
            )
        self.assertEqual(error_context.exception.product, "kubernetes")
        self.assertEqual(error_context.exception.version, "1.30")
        self.assertEqual(error_context.exception.supported_versions, ("1.28", "1.29"))

    def test_returns_mock_result(self) -> None:
        result = self.registry.investigate(
            InvestigationRequest(product="postgresql", version="16")
        )
        self.assertEqual(result.product, "postgresql")
        self.assertEqual(result.version, "16")
        self.assertIn("Mock PostgreSQL investigation", result.summary)
        self.assertEqual(result.findings["replication_lag_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
