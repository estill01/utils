# Typed initialized session

Block 6 adds one initialize/initialized handshake and the eight frozen typed
request methods. It composes the accepted compatibility result, byte transport,
and private RPC engine. It does not add a raw RPC escape, events, callbacks,
automatic cancellation, restart, product records, or policy.

## Ownership and handshake

`AppServerClient.connect(transport, compatibility, limits=ClientLimits())`
checks the exact compatibility and active transport capability before claiming
the transport. `initialize(ClientIdentity(...))` is available exactly once and
performs this order:

1. send the official `initialize` request with the exact client identity;
2. declare `experimentalApi=false`, no extensions, no legacy MCP form
   elicitation, and no attestation request;
3. opt out of the 55 retained notifications outside the exact selected set,
   after installing the bounded Block 7 notification/callback coordinator;
4. validate the complete initialize response against the retained official
   schema; and
5. send the parameter-free `initialized` notification before returning the
   session.

An invalid or interrupted handshake closes the one owned connection. Duplicate
or changed initialization is rejected and cannot create another session.
`AppServerSession.close()` delegates to the same client owner; cancellation of
a close waiter does not cancel cleanup, and later close calls retrieve the same
typed cleanup result.

## Exact operation surface

| Python method | Protocol method | Parameter/result models |
|---|---|---|
| `start_thread` | `thread/start` | `ThreadStartParams` / `ThreadStartResponse` |
| `resume_thread` | `thread/resume` | `ThreadResumeParams` / `ThreadResumeResponse` |
| `read_thread` | `thread/read` | `ThreadReadParams` / `ThreadReadResponse` |
| `list_threads` | `thread/list` | `ThreadListParams` / `ThreadListResponse` |
| `start_turn` | `turn/start` | `TurnStartParams` / `TurnStartResponse` |
| `steer_turn` | `turn/steer` | `TurnSteerParams` / `TurnSteerResponse` |
| `interrupt_turn` | `turn/interrupt` | `TurnInterruptParams` / `TurnInterruptResponse` |
| `start_review` | `review/start` | `ReviewStartParams` / `ReviewStartResponse` |

Each operation accepts only its named model. The request capability must exist
in the exact Block 3 `FeatureSet`, and the result must decode as the matching
retained response schema. Invalid results fail the connection with a
content-free `JsonRpcValidationError`. There is no public method-string,
payload-dictionary, request-ID, or byte-write API.

The composed Block 7 session reports the eight implemented request
capabilities, 15 selected notification capabilities, three selected callback
capabilities, and only the active transport. A peer that sends an unselected
notification or callback fails the connection closed and cannot publish or
corrupt a typed result.

## Frozen model graph

The public parameter and result classes and every transitively reachable named
definition are generated deterministically at import from the wheel-retained
Codex `0.147.0` schemas. Same-name unequal definitions fail closed. Object
models are frozen and slotted; required fields have no default, optional fields
default to `None`, arrays normalize to tuples, string enums become closed
`StrEnum` classes, and schema unions remain closed Python unions. Inbound
operation results, notifications, callback parameters, and initialization
results deep-freeze additional JSON when `additionalProperties` is omitted or
`true`. Outbound operation parameters, callback responses, and initialization
parameters reject unknown fields unless the schema explicitly permits them.

Serialization produces only schema field names and plain JSON values. Model and
session validation errors identify the contract location but never retain or
expose request/result content.

## Stop boundary

The typed request layer itself does not interpret server notifications or choose
callback decisions. The composed Block 7 coordinator owns their transport and
termination mechanics. Restarting a process, replacing a generation, choosing
approval policy, or operating an external consumer remains outside this layer.
