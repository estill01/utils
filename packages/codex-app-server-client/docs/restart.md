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

Replacement accepts only an exact package-owned `StdioTransport`,
`UnixSocketTransport`, or cleanup-proven owned `InjectedTransport`. Arbitrary
structural transports are valid initial connection inputs but cannot prove that
a fresh wrapper is a fresh underlying wire, so they are rejected before claim
on replacement. Borrowed injected transports are also rejected for replacement.
An owned injected replacement is available only when the client's lifetime
began on package-owned, cleanup-proven transport construction; a client that
began on a structural or borrowed injected transport may recover only through a
fresh package-owned stdio process or Unix-socket connection.

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

The client also retains connection-lineage identity for its lifetime. An owned
`InjectedTransport` cannot reuse a caller-supplied `ByteChannel` object already
claimed by that client. Rejection occurs before the proposed transport is
claimed or a replacement reader can consume late responses, notifications, or
callbacks. The declared package lineage and actual opened `ByteChannel` are
checked independently. Unprovable or non-weak-referenceable identities fail
closed. Once a transport has opened a channel, both identities are recorded
before either acceptance or cleanup, so a rejected post-open attempt cannot
make that channel eligible for a later generation. The client retains only weak
identity references, prunes dead lineages, and bounds simultaneously live
history with a fixed private package capacity. Distinct client owners remain
independent; this is not an ambient channel registry, public retry budget, or
process singleton.

After retirement, an old session, callback, selected response, or close attempt
raises `StaleGenerationError` and cannot read, write, publish, cancel, or close
the current generation. Cancellation, timeout, late response, and cleanup state
remain owned by the engine on which they began. A failed or cancelled
replacement attempt is cleaned before a later attempt advances to another
generation.

Cancellation is attributed by the current task's outstanding cancel count.
Caller cancellation remains cancellation and is re-raised after retained
cleanup. A synchronous hook, lineage provider, channel operation, or transport
start that raises `CancelledError` without an outstanding caller cancellation
is a component failure; it is normalized to a content-free typed failure and
cannot strand an unproven process or channel owner. Caller cancellation during
transport start is terminal for that client because the claimed transport may
already have created a resource; later replacement and close fail without
claiming another owner or implying that cleanup was proved.

## Stop boundary

This layer contains no automatic retry loop, retry budget, exponential-backoff
policy, provider selection, process pool, remote failover, durable event
ledger, supervision decision, downstream adapter, or product acceptance.
