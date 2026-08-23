# embedded-service-contract

Independently versioned structural lifecycle protocols and conformance helpers
for embedded and service-shaped hosts. Block 1 provides only the import/version
skeleton; Block 10 owns its neutral behavior and fixtures.

The package defines five generic operations—start, status, ordered events,
idempotent cancel, and terminal outcome—without defining request, event,
result, or failure meanings. Embedded hosts declare no process owner;
service-shaped composition declares exactly one host process owner. The
contract starts no process and provides no server, runner, persistence,
scheduler, provider, or product lifecycle.

Two deliberately separate in-memory reference hosts and reusable negative
fixtures live in `embedded_service_contract.testing`. They prove the same
structure using direct typed state and service-shaped mapping records without
sharing an execution runtime. Every reference carries deterministic
per-instance lineage so one host cannot mistake another host's run for its own.

```python executable
from embedded_service_contract import assert_lifecycle_conformance
from embedded_service_contract.testing import embedded_fixture, service_fixture

embedded = assert_lifecycle_conformance(embedded_fixture())
service = assert_lifecycle_conformance(service_fixture())

assert embedded.scenarios == service.scenarios == 3
assert embedded.shape.value == "embedded"
assert service.shape.value == "service"
```

The frozen structural, conformance-fixture, and supported-Python records are
under `contract/` and are retained inside the wheel. They are descriptive test
contracts only, not runtime authority or consumer adoption records.

This distribution is currently unlicensed and unpublished.
