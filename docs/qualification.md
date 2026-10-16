# Technical package-set qualification

`tools/qualification_matrix.json` freezes the current repository-owned package
set for deterministic CI verification. The unchanged Block 14 record is retained
in `tools/history/qualification-0.1.0.json`; the prior `0.2.0` candidate is
retained in `tools/history/qualification-0.2.0.json`. The prior `0.3.0` record is retained in
`tools/history/qualification-0.3.0.json`. The prior `0.4.1` record is retained in `tools/history/qualification-0.4.1.json`. These are historical evidence only. The current record reconciles each distribution's accepted source,
version, wheel bytes, wheel content root, public contract inputs, executable
README example, Python matrix, protocol roots, composition roots, and empty
runtime-dependency inventory.

The technical-source root covers every tracked file and its Git mode at the
recorded candidate revision except the mutable tracker evidence and the
self-referential qualification JSON. An exact acceptance run additionally
passes the expected current `HEAD`, so added, removed, changed, or mode-changed
technical files cannot reuse earlier proof.

The current record is a `candidate`, not a claim that unrun tests passed. CI
results belong to the exact pushed revision and its actual completed jobs. The
historical `program-qualified` posture applies only to the old frozen package
set. Neither record is a production acceptance, release, license, or grant of
reuse rights.

The prior `0.4.2` record is retained byte-for-byte in `tools/history/qualification-0.4.2.json`.

The current client is `0.5.0`. Its default facade remains exactly `0.147.0`;
the explicit `v0_162_1` facade retains the official stable `0.162.1` source
schemas. The explicit `v0_156_1` facade adds the exact stable 0.156.1 schemas,
bounded persisted turn and item pages and borrowed local WebSocket attachment. Its
synchronous request guard is checked after transport lock waits, before writing
bytes. All three profiles have deterministic typed model/session tests, while
real `0.162.1` executable and model-work qualification remains unrun. The
neutral three-package composition continues to exercise the default profile.
The two sibling runtime packages remain unchanged at `0.1.0`. Build-only inputs
are pinned in `tools/build-constraints.txt`; the maintained runners set
`SOURCE_DATE_EPOCH=1580601600` and use those constraints for isolated builds.
Wheel and content roots are newly measured, never relabeled historical proof.
No official-Codex or model execution is part of this CI qualification.

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
