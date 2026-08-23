# Development and compatibility policy

## Maintained invocation envelope

The repository-owned checks are:

```bash
python3 scripts/check_quality.py
python3 scripts/check_package.py --all --python 3.11 --tests
python3 scripts/check_package.py --all --python 3.14 --tests
```

`scripts/check_package.py` resolves the repository root from its own location,
uses the configured `uv` executable, copies each distribution into an isolated
package-only snapshot, and builds each wheel independently. It audits wheel
metadata and Python imports against the admitted dependency graph, rejects
unadmitted, circular, reverse, or undeclared dependencies, creates a clean
temporary environment, installs only that wheel without dependencies, imports
it from outside the checkout, and runs the copied package-local test contract.
The `--all` jobs execute in parallel but never share an environment or install
another distribution. The isolation command requires `--tests` and fails if a
package-local test directory is missing, contains no `test_*.py` files, or
executes zero tests.
`scripts/check_quality.py` runs the repository contract plus the exact uv/Ruff
versions pinned in `tools/toolchain.json`; CI invokes the same envelope.

## Version policy

- Every distribution starts at `0.1.0` and versions independently.
- While a distribution is `0.y`, a minor release may change its public API only
  with an explicit compatibility note; patch releases remain backward
  compatible within the supported upstream/schema contract.
- After `1.0.0`, incompatible public API changes require a major version.
- Version changes occur only in the owning package metadata and import root.
- This repository has no root distribution and no aggregate version.

## Python and compatibility baseline

- Supported Python: CPython 3.11 or newer.
- CI exercises the lower bound and a current interpreter.
- App-server protocol/schema compatibility is frozen by Blocks 2–3.
- Structural-contract and manifest-schema compatibility are owned by Blocks 10
  and 11 respectively.

## Changed-test mapping

`tools/changed_tests.json` and `scripts/changed_test_plan.py` map package-local
changes to one package job and shared tooling/documentation changes to all
package jobs. The mapping selects repository-owned checks only; it never opens
or runs a downstream consumer suite.

## Release posture

Builds are internal qualification artifacts. No license has been selected, the
distributions are unpublished, and the CI workflow contains no publication or
release credentials/effects.
