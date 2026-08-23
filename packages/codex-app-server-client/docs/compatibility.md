# Compatibility owner

Block 3 implements only executable identity and schema compatibility. It does
not start `app-server`, allocate a request ID, open a socket, or create a byte
transport.

`resolve_codex_binary()` resolves one exact executable. A path-like argument is
used exactly. A bare name or the default `codex` is searched across `PATH`; no
match raises `CodexBinaryNotFoundError` and more than one distinct resolved
file raises `AmbiguousCodexBinaryError`. The resolved file is hashed and
`--version` must produce a parseable `codex-cli X.Y.Z` result.

`inspect_compatibility()` accepts a previously probed `BinaryIdentity`. With no
`schema_dir`, it reads the wheel-retained official schemas and performs no
subprocess or transport operation. An explicit directory supports a bounded
currentness check of newly generated schemas.

Compatibility requires all of:

- the exact `ProtocolTarget` and Codex `0.147.0`;
- retained byte root
  `eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`;
- semantic root
  `4e5c64213673b670d2575d7b7670d2089d49f92a92c56f2d16618e4a8857813e`;
- 285 retained/generated JSON files and the retained 2,925,973-byte count;
- selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`;
  and
- presence of every frozen initialize, request, notification, and callback
  method in its official union.

The semantic root is SHA-256 over sorted lines of
`<canonical-json-sha256>  <relative-path>\n`. Canonical JSON uses sorted keys,
compact separators, UTF-8, and non-ASCII preservation. Formatting-only changes
therefore preserve the semantic root; content or path changes do not.

Run the ordinary installed-wheel suite without an official binary:

```bash
python3 scripts/check_package.py \
  --package codex-app-server-client --python 3.11 --tests
```

Run one candidate-freeze currentness check with an explicit executable:

```bash
PYTHONPATH=packages/codex-app-server-client/src \
python3 scripts/check_app_server_currentness.py --codex /absolute/path/to/codex
```

The currentness command invokes only `--version` and
`app-server generate-json-schema --out <temporary-directory>` without
`--experimental`. It never starts `app-server`. The temporary tree is removed
after comparison.
