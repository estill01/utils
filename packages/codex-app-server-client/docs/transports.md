# Local transport ownership

The package exposes exactly three local transport configurations. Every
transport instance is single-use: one later client owner claims one channel,
and a second claim raises `TransportOwnershipError`. There is no process,
connection, or ownership singleton.

## Owned stdio

`StdioTransport(BinaryIdentity)` rechecks the exact absolute executable path,
version, stable file identity, executability, and SHA-256 before and after
start. It invokes an argv vector—never a shell command—with the exact local
stdio selection:

```text
<exact-binary> app-server --listen stdio://
```

stdin and stdout carry JSON lines and stderr is discarded rather than retained
in package errors. On POSIX, the process starts in a new session and the
returned channel owns that complete process group, including the wrapper and
native descendants. Close first closes stdin, allows a short EOF exit, then
escalates the owned process/group through terminate and kill with bounded
waits. It does not return from successful cleanup until the direct child has
been reaped and the owned group is absent; failure to prove either raises
`TransportCleanupError`.

## Unix socket

`UnixSocketTransport(path)` opens one client connection to an explicit local
Unix-domain socket. It creates no listener and owns no process. Paths must be
absolute, contain no parent traversal or NUL, and fit the conservative
cross-platform Unix-socket path bound. Relative, byte, traversal, and oversized
paths fail before I/O. TCP, WebSocket, remote proxy, daemon discovery, and
ambient control-socket lookup are absent.

## Injected channel

`InjectedTransport(channel, ownership=...)` wraps a caller-supplied
`ByteChannel` with the same framing, byte-bound, serialized-write, close, and
content-minimized error behavior as concrete streams. `OWNED` closes the
underlying channel exactly once. `BORROWED` cancels package-owned active
operations and closes only its wrapper, leaving the underlying channel open for
its caller owner.

All modes return one newline-delimited byte channel with serialized writes,
bounded reads, typed EOF/post-close/cleanup failures, and no retained
request/response/channel exception content. They do not initialize app-server,
send a request, interpret a message, dispatch callbacks or events, retry, or
restart. Cancelling a write fail-closes its wrapper before another writer can
enter, and cancelling `close()` cannot cancel the retained cleanup task; a
later close awaits the same cleanup result. Tests use deterministic in-memory
channels, disposable executable/process-group fixtures, and temporary local
Unix sockets only.
