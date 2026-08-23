# Bounded RPC core

The RPC core owns only transport-independent request/response mechanics. It
accepts a previously proven `CompatibilityResult` and an injected
`ByteChannel`; it does not resolve or start a binary, open a subprocess or
socket, initialize a session, dispatch notifications or callbacks, retry, or
restart.

`ByteChannel` is the minimal boundary shared with later concrete transports:

- `read_line(max_bytes=...)` returns one `bytes` record including one terminal
  line feed;
- `write_line(data)` receives one complete encoded record including its line
  feed; and
- `close()` closes the channel and unblocks any active read.

The engine checks the byte limit itself even when a channel also enforces the
hint. It accepts LF or CRLF termination, rejects embedded line feeds, missing
termination, invalid UTF-8, duplicate JSON object keys, nonstandard numeric
constants, non-object responses, and invalid retained-schema envelopes.

The official retained `JSONRPCRequest`, `JSONRPCResponse`, and `JSONRPCError`
schemas are the envelope authority. They do not require a `jsonrpc` field, so
the core does not invent one. Although the upstream `RequestId` schema also
allows strings, this package deliberately narrows correlation to positive
bounded `int64` values and rejects booleans, strings, zero, and negative IDs.
Only closed `RequestCapability` values proven by the compatibility result can
be sent; request-ID allocation and arbitrary method strings remain private.

Pending calls are registered before their line is written, capped by a fixed
limit, resolved once by exact integer ID, and removed on success, remote error,
caller cancellation, timeout handoff, close, or protocol failure. One late
response to a timed-out or cancelled call is consumed without resurrecting the
call. Unmatched or duplicate responses fail the channel as `CorrelationError`
and fail all remaining calls without retaining pending state.

Validated remote errors expose only their request ID, integer code, and whether
data was present. The arbitrary remote message and `data` payload are not kept
on the public exception. Framing, validation, size, capacity, correlation, and
remote failures use distinct subclasses of `AppServerClientError`; none logs
request or response content.

The focused tests use a deterministic in-memory peer implementing only
`ByteChannel`. They exercise concurrent out-of-order responses, remote errors,
malformed records, invalid and duplicate IDs, timeout/cancellation handoff,
capacity and byte limits, peer closure, exact cleanup, and absence of concrete
transport dependencies.
