# Distribution conformance

Block 9 freezes the complete `codex-app-server-client==0.1.0` distribution
without adding protocol methods, transports, retry policy, or product behavior.

The installed-wheel matrix runs from outside the checkout and covers the exact
92-export public root, all eight typed operations, all fifteen selected server
notifications, all three policy-neutral callback families, explicit close,
failure, and generation-safe replacement. `tests/fake_app_server.py` is the
single deterministic JSON-lines peer for that matrix. It creates no process,
socket, file, repository, or ambient singleton.

Run the complete source and installed-wheel matrices with:

```bash
PYTHONPATH=packages/codex-app-server-client/src \
python3 -m unittest discover \
  -s packages/codex-app-server-client/tests -p 'test_*.py' -v

python3 scripts/check_package.py \
  --package codex-app-server-client --python 3.11 --tests
```

At one frozen candidate, run the explicit official-binary smoke:

```bash
PYTHONPATH=packages/codex-app-server-client/src \
python3 scripts/smoke_app_server_client.py \
  --codex /absolute/path/to/codex --timeout 15
```

The smoke resolves and hashes only that executable, verifies the retained
compatibility roots, owns one local stdio app-server process, initializes one
generation, performs one bounded typed thread-list request, and closes the
process. It does not inspect or mutate any consumer repository.

This package has no selected license and is unpublished. Conformance acceptance
is an internal exact-revision package handoff; it is not publication, release,
redistribution authority, or a claim that any downstream consumer adopted it.
