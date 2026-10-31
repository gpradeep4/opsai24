# opsai24

OpsAI24 Feature 1 introduces a technology investigation plugin framework with
stable interfaces, models, a central registry, unsupported-product/version
handling, and deterministic mock plugins for local development.

## Architecture

The implementation lives under `opsai24/technology/`:

- `models.py` defines stable request/result data models:
  - `InvestigationRequest(product, version, context)`
  - `InvestigationResult(product, version, summary, findings)`
- `interfaces.py` defines the stable plugin interface:
  - `TechnologyInvestigationPlugin`
- `registry.py` provides `PluginRegistry` to:
  - register plugins by product
  - list supported products
  - route investigation requests
  - enforce unsupported product/version checks
- `exceptions.py` defines typed errors:
  - `DuplicatePluginError`
  - `UnsupportedProductError`
  - `UnsupportedVersionError`
- `mock_plugins.py` provides two local-only mock plugins:
  - `KubernetesMockPlugin` (versions `1.28`, `1.29`)
  - `PostgreSQLMockPlugin` (versions `15`, `16`)

No remote execution is performed; plugins return deterministic mock findings.

## Example Usage

```python
from opsai24.technology import (
    InvestigationRequest,
    KubernetesMockPlugin,
    PluginRegistry,
)

registry = PluginRegistry()
registry.register(KubernetesMockPlugin())

result = registry.investigate(
    InvestigationRequest(product="kubernetes", version="1.29")
)
print(result.summary)
print(result.findings)
```

## Tests

Run the unit tests:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
