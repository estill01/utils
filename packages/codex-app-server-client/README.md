# codex-app-server-client

Independently versioned Python support for exact Codex app-server
compatibility, local transports, typed sessions, asynchronous coordination, and
generation-safe restart. Block 1 provides the import/version skeleton. Block 2
freezes the exact upstream target and deliberately narrowed public contract;
Blocks 3–9 own its behavior and conformance.

API candidate `0.3.0` preserves the root `codex_app_server_client` facade at
exact Codex `0.147.0` and adds the explicit
`codex_app_server_client.v0_162_1` facade for exact `0.162.1`. Import the facade
that matches the executable you intend to use; profiles are never guessed,
negotiated, or changed on replacement. Each has its own immutable typed models,
notifications, callbacks, schema validation, and executable-version gate while
sharing the bounded transport/RPC/session lifecycle. Models from one profile
cannot be sent through the other profile's session or callbacks.

For a `0.162.1` host, use `from codex_app_server_client import v0_162_1 as codex`
and call that facade's `inspect_compatibility`, `StdioTransport`,
`AppServerClient`, and model constructors. The same eight request methods,
fifteen notification families, and three callback families are supported in
both profiles. Unknown traffic remains fail-closed. The new `writeStdin`
command-approval kind is typed; authorization remains the consumer's decision.

The `0.162.1` schemas come byte-for-byte from the official tagged source's
precomputed stable JSON bundle. This source and deterministic fixture evidence
is not a real-executable or paid-model qualification. See
`protocol/README.md` for exact provenance and scope.

The immutable `session.initialize_info` and content-free
`RemoteRpcError.category` added in `0.2.0` remain available in both profiles.
Earlier qualification records remain historical; no previous runtime smoke is
relabeled as a `0.3.0` or `0.162.1` result.

The frozen protocol contract is in `docs/protocol-contract.md`, its Block
ownership proof is in `docs/proof-map.md`, and the complete non-experimental
official schema snapshot and manifest are under `protocol/`. Those artifacts
do not expose every upstream method: `protocol/supported-surface.json` is the
closed supported feature set and `protocol/public-api.json` is the exact future
root-export, signature, schema-model, capability, and error contract.

Block 4's transport-independent request-state behavior and injected-channel
contract are documented in `docs/rpc.md`.
Block 5's explicit local transport and resource-ownership behavior is in
`docs/transports.md`.
Block 6's exact initialize handshake, immutable schema-model graph, and eight
typed request methods are in `docs/session.md`.
Block 7's bounded event/callback streams and exact call-termination behavior
are in `docs/coordination.md`.
Block 8's generation-bound connection replacement and caller-owned bounded
backoff hook are in `docs/restart.md`.
Block 9's complete installed-wheel matrix, deterministic fake, and bounded
official-binary smoke are in `docs/conformance.md`.

The public configuration objects are ordinary frozen values:

```python executable
from codex_app_server_client import ClientIdentity, ClientLimits, TransportOwnership

identity = ClientIdentity("host", "1.0")
limits = ClientLimits(max_pending_calls=32, max_events=64, max_callbacks=8)

assert identity.to_dict() == {"name": "host", "version": "1.0"}
assert limits.max_pending_calls == 32
assert TransportOwnership.OWNED.value == "owned"
```

This distribution is currently unlicensed and unpublished.
