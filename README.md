# opsai24

OpsAI24 Feature 1 introduces a technology investigation plugin framework with
stable interfaces, models, a central registry, unsupported-product/version
handling, and deterministic mock plugins for local development.

OpsAI24 Feature 2 introduces an investigation lifecycle domain and service with
framework-independent state management, idempotent incident intake, and local
persistence abstraction.

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

## Investigation Lifecycle (Feature 2)

The investigation lifecycle implementation lives under `opsai24/investigation/`:

- `models.py`
  - `Investigation` record model
  - lifecycle states: `QUEUED`, `RUNNING`, `COMPLETED`, `PARTIAL`, `FAILED`, `CANCELLED`
  - transition validation rules, including guard against returning to `RUNNING`
    from any terminal state
- `service.py`
  - `InvestigationService` for create/transition/progress/status operations
  - idempotent creation by `source_event_id`
  - optimistic concurrency via `expected_revision` to prevent silent overwrite
  - sanitization for persistence errors and sensitive metadata fields
  - evidence references stored as ID-only tuples
- `persistence.py`
  - `InvestigationStore` abstraction
  - `InMemoryInvestigationStore` minimal local adapter
- `exceptions.py`
  - typed lifecycle/persistence errors

### Service usage example

```python
from opsai24.investigation import (
    InMemoryInvestigationStore,
    InvestigationService,
    InvestigationState,
)

store = InMemoryInvestigationStore()
service = InvestigationService(store)

created = service.create_investigation(
    source_event_id="incident-001",
    product="kubernetes",
    version="1.29",
    evidence_ids=["ev-12", "ev-15"],
)

running = service.transition_state(
    investigation_id=created.investigation_id,
    next_state=InvestigationState.RUNNING,
    expected_revision=created.revision,
)

current = service.get_status(running.investigation_id)
print(current.state, current.progress_percent)
```

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
python3 -m unittest discover -s tests -p "test_*.py" -v
```
