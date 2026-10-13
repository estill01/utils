# Exact retained protocol profiles

The package exposes two separate, frozen app-server profiles:

- `codex_app_server_client` retains Codex **0.147.0**, its 285 schemas,
  existing public API, default target, and recorded binary-generation provenance.
- `codex_app_server_client.v0_162_1` explicitly selects Codex **0.162.1**
  and its 317 stable schemas. Its runtime models, callbacks, and client generations
  are bound to this profile. Importing it does not change the root profile.

Neither profile is a version range, an automatic version selector, or a custom
schema registry. Both retain exactly eight selected requests, fifteen selected
notifications, three policy-neutral callbacks, and the same three transports.

## Provenance boundary

The legacy `upstream-manifest.json`, `compatibility.json`, and `public-api.json`
remain byte-for-byte unchanged. Its recorded wrapper/native binary evidence is
historical evidence for 0.147.0 only.

The 0.162.1 manifest records **source-bundle acquisition**, not a local binary
schema-generation run:

- Official repository: <https://github.com/openai/codex>
- Tag: `rust-v0.162.1`
- Tag object: `7a078f6bb4ce0dc2a81408b334ce52979d92c603`
- Source commit: `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`
- Bundle: `codex-rs/app-server-protocol/schema/precomputed/app-server-exports-stable.json.zst`
- Bundle SHA-256: `ed720775cdc264c7c5a930d582c56a27f5f8b18408187f783f93b9713ed40d48`
- Retained content: the bundle's `json_schema` map, using each string's exact
  UTF-8 bytes. All 317 files also match the official commit's checked-in
  `codex-rs/app-server-protocol/schema/json` files byte-for-byte.

The checked-in source implements stable JSON generation by writing this
precomputed map. That source fact does not claim that a 0.162.1 executable was
installed, launched, probed, or qualified here. The manifest deliberately contains
no wrapper hash, native executable hash, or fabricated generation command.

## Offline checks

From the repository root:

```sh
python scripts/check_protocol_contract.py
python scripts/test_protocol_contract.py
python scripts/public_api_signatures.py
python scripts/test_public_api_signatures.py
```

The contract check verifies **both** retained profiles by default, including
exact file manifests, byte and semantic tree roots, surface roots, API manifest
hashes, actual runtime exports, and actual public signatures with resolved type
annotations. `--profile 0.147.0` or `--profile 0.162.1` checks only that profile.
Fixture override options require an explicit profile and are intended for
fail-closed tests. None of these checks runs a Codex executable.

`public-api-signatures.json` records inspectable constructors, lifecycle and
operation methods, properties, callback responses, and capability enums for each
facade. These additive fixtures preserve the legacy API manifest's original hash.
Changes to either fixture are pinned by `check_protocol_contract.py` and require
explicit contract review; `public_api_signatures.py --write` only regenerates
snapshots and does not update those pins automatically.

These checks establish source-schema and offline API compatibility. They are not
host-native executable qualification, a package release, or publication evidence.
