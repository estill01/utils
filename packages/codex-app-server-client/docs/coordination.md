# Asynchronous coordination

Block 7 adds one bounded coordinator to the initialized connection. It keeps a
single read pump active across responses, selected notifications, and selected
server requests; IDs and payload dictionaries remain private.

## Selected event stream

Initialization opts out of the 55 unselected methods in the retained set of
70 server notifications. The remaining 15 methods decode to their exact frozen
notification models and form the closed `ServerEvent` union. One active
`session.events()` iterator receives them in wire order. Concrete model type is
the tag; no raw method field is added.

Undelivered events are bounded by `ClientLimits.max_events`. The sole read pump
never waits for event capacity, because doing so could deadlock unrelated RPC
responses. Capacity exhaustion therefore preserves already queued events,
fails the connection with `RequestLimitError`, and then terminates the iterator;
no event is silently evicted or duplicated.

## Policy-neutral callbacks

`session.callbacks()` exposes a closed union of three privately constructed
wrappers:

- `CommandExecutionApprovalCallback`;
- `FileChangeApprovalCallback`; and
- `UserInputCallback`.

Each wrapper exposes only typed `params` and one `respond(exact_response)`
method. The caller supplies every approval, cancellation, amendment, or answer;
the package selects no default and interprets no product outcome. Official
callback IDs remain private, accept strings or signed int64 values, live in a
namespace separate from positive-integer client call IDs, and are echoed
unchanged in the private response envelope.

`ClientLimits.max_callbacks` counts every unresolved callback, including one
already yielded to a caller. Taking an item from the iterator does not release
capacity. A callback atomically claims its response before any write; a wrong
response type, second response, concurrent response, or post-termination
response cannot produce another wire write. Cancelling the response waiter
returns `CallCancelledError` while the already selected response continues to
one terminal write.

## Terminal behavior

- A request deadline raises `CallTimeoutError`; its one late response is
  consumed privately and cannot become another result.
- Direct asyncio task cancellation remains `asyncio.CancelledError`; any
  selected request write completes safely and a late response is ignored.
- Explicit close ends event and callback iterators cleanly and gives pending
  calls or unanswered callback handles `CallCancelledError`.
- Unexpected read/write loss raises `DisconnectedError`, wakes all iterator and
  call waiters, invalidates unanswered callbacks, and closes the channel once.
- Malformed, unselected, duplicate, over-capacity, or mixed inbound envelopes
  fail closed with the existing discriminating content-free errors.

Queued valid events drain before an unexpected terminal error is raised.
Unanswered callbacks cannot be useful after termination, so queued callback
handles are invalidated rather than published stale. Only one iterator per
stream may be active at a time, preventing accidental load-balanced delivery.

## Accepted schema-label caveat

The official non-experimental Codex `0.147.0` generation includes the selected
plan-delta and user-input schemas even though their upstream descriptions call
them experimental. Block 2 explicitly froze those exact files and methods into
the selected-surface and public-API roots, so this implementation preserves
them. The label grants no general experimental API support; removing or
replacing either selection requires a separately reviewed Block 2 contract
change.

## Stop boundary

This coordinator does not restart a process, replace a connection, apply
backoff, cross generations, choose approval policy, persist events, interpret
workflow outcomes, or operate any external consumer.
