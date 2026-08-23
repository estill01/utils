# Generation-bound replacement

Block 8 adds one policy-neutral replacement operation above the accepted
transport, session, and asynchronous coordination layers. A caller may replace
only a failed connection and must supply a new single-use `ClientTransport`.
The client reuses the exact accepted compatibility result, limits, and
`ClientIdentity`; it never discovers a process, chooses a transport, or decides
whether or when a product should retry.

## Public replacement contract

`await client.replace(transport, backoff=hook)` serializes with initialization,
another replacement, and close. It returns the one initialized
`AppServerSession` for the next integer generation. A healthy, closing, or
closed client rejects replacement with `RestartError`, and concurrent callers
cannot claim two replacement transports.

When supplied, the synchronous `BackoffHook` is called exactly once with an
immutable `RestartContext(failed_generation, replacement_generation, cause)`.
Its numeric delay must be finite, non-negative, and no greater than
`ClientLimits.max_backoff_seconds`. The hook owns only that delay decision; an
invalid result or hook failure occurs before the proposed transport is claimed
and is reported without retaining hook content.

## Generation isolation

Every session keeps immutable references to its generation's engine and
coordinator. Replacement retires and quiesces the failed engine before opening
the next transport, clears queued old events and callbacks, invalidates old
callback handles, and joins retained request and callback writes. Publication
checks occur before an event, callback, or typed response crosses the public
session boundary.

After retirement, an old session, callback, selected response, or close attempt
raises `StaleGenerationError` and cannot read, write, publish, cancel, or close
the current generation. Cancellation, timeout, late response, and cleanup state
remain owned by the engine on which they began. A failed or cancelled
replacement attempt is cleaned before a later attempt advances to another
generation.

## Stop boundary

This layer contains no automatic retry loop, retry budget, exponential-backoff
policy, provider selection, process pool, remote failover, durable event
ledger, supervision decision, downstream adapter, or product acceptance.
