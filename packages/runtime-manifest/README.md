# runtime-manifest

Independently versioned deterministic metadata for exact component, protocol,
schema, capability, feature, and dependency compatibility.

The package accepts only caller-supplied records. It does not inspect installed
packages, the filesystem, a registry, or a network, and it cannot express
authorization, acceptance, product identity, or availability decisions.
Compatibility means only that an observed manifest contains the exact required
versions and roots; unrelated observed records are allowed.

```python executable
from runtime_manifest import canonical_json, compare_manifests, parse_manifest
from runtime_manifest.testing import neutral_expected, neutral_observed

expected = neutral_expected()
observed = neutral_observed()

assert parse_manifest(canonical_json(expected)) == expected
assert compare_manifests(expected, observed).compatible
```

The frozen manifest schema, compatibility fixtures, public API record, and
supported-Python record are under `contract/` and retained inside the wheel.
They are descriptive compatibility inputs only and grant no runtime authority.

This distribution is currently unlicensed and unpublished.
