# Technical package-set qualification

`tools/qualification_matrix.json` freezes the exact repository-owned package
set accepted by Block 14. It reconciles each distribution's accepted source,
version, wheel bytes, wheel content root, public contract inputs, executable
README example, Python matrix, protocol roots, composition roots, and empty
runtime-dependency inventory.

The technical-source root covers every tracked file and its Git mode at the
recorded candidate revision except the mutable tracker evidence and the
self-referential qualification JSON. An exact acceptance run additionally
passes the expected current `HEAD`, so added, removed, changed, or mode-changed
technical files cannot reuse earlier proof.

The record is technical evidence only. `program-qualified` means that this
repository's complete internal matrix passed for the frozen package set. It is
not a consumer pin, installation instruction, availability statement,
production acceptance, release, license, or grant of reuse rights.

Run the static reconciliation first:

```bash
python3 scripts/check_qualification.py
```

Then run the complete frozen matrix exactly once for a candidate:

```bash
python3 scripts/check_quality.py --expected-head <exact-pushed-revision>
python3 scripts/check_package.py --all --python 3.11 --tests
python3 scripts/check_package.py --all --python 3.14 --tests
python3 scripts/check_composition.py --python 3.11
python3 scripts/check_composition.py --python 3.14
```

The isolated jobs build and install each distribution alone. The composition
jobs build the same accepted wheel bytes, install only those three local
artifacts together, and exercise the neutral public-only fixture. Package-local
tests execute each marked README example and compare installed public APIs to
their retained exact records. No command opens, imports, invokes, mutates, or
validates a downstream consumer.

The qualification remains `no-license-selected/unpublished`. Repository
visibility does not make any distribution publicly installable, reusable, or
redistributable.
