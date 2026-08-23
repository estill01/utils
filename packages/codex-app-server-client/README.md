# codex-app-server-client

Independently versioned Python support for exact Codex app-server
compatibility, local transports, typed sessions, asynchronous coordination, and
generation-safe restart. Block 1 provides the import/version skeleton. Block 2
freezes the exact upstream target and deliberately narrowed public contract;
Blocks 3–9 own its behavior and conformance.

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

This distribution is currently unlicensed and unpublished.
