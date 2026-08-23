# App-server client proof map

| Owner | Frozen responsibility | Required proof | Stop boundary |
|---:|---|---|---|
| Block 3 | exact binary/version resolution, retained/generated schema loading, semantic root, selected feature compatibility | exact/stale/missing/malformed/incompatible fixtures; no process or socket start | before JSON-RPC state or transport |
| Block 4 | bounded newline-delimited JSON-RPC over an injected byte channel | framing, validation, integer IDs, concurrent correlation, limits, remote errors, pending cleanup | before subprocess or Unix socket |
| Block 5 | owned stdio, Unix socket, and injected transport implementations | shared byte-channel conformance; argv, ownership, serialization, EOF, close, cleanup | before initialize or typed methods |
| Block 6 | initialize/initialized handshake and eight selected typed request methods | handshake order, declared capabilities, per-method gates, typed models, no raw escape | before events, callbacks, cancellation, or restart |
| Block 7 | selected typed notifications and three policy-neutral callback families, cancellation/timeouts/disconnect | forced interleavings, queue/callback bounds, attribution, exactly-once terminal results | before restart/backoff or generation replacement |
| Block 8 | generation-bound replacement and caller-supplied bounded backoff hook | exact old/new generation race schedules at every publication and termination edge | before distribution qualification |
| Block 9 | complete wheel-installed conformance and one official-binary smoke | public API fixture, deterministic fake server, lifecycle matrix, artifact and compatibility roots | before other packages or cross-package work |

No owner may add an upstream method, transport, event, callback, error fallback,
consumer type, or policy that is not selected in the frozen contract. An owner
that discovers a required contract change stops and returns it to Block 2
review rather than widening its own implementation.
