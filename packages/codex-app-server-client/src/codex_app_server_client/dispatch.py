"""Caller-owned synchronous preconditions at a request's final local write."""

import inspect
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .errors import AppServerClientError


class DispatchRejectedError(AppServerClientError):
    """A selected request was rejected before any of its bytes were written."""


_guard: ContextVar[Callable[[], None] | None] = ContextVar("request_dispatch_guard", default=None)


@contextmanager
def dispatch_guard(check: Callable[[], None]) -> Iterator[None]:
    """Guard typed requests in this task, including asynchronous write tasks.

    The callback must return None synchronously or raise. It runs after all
    local write locks, immediately before bytes are passed to the transport.
    Package-owned stream/WebSocket transports support this; injected channels
    without guarded_write_line reject guarded requests before writing.
    It does not control remote execution after bytes have been dispatched.
    """
    if not callable(check):
        raise TypeError("dispatch guard must be callable")
    token = _guard.set(check)
    try:
        yield
    finally:
        _guard.reset(token)


def _check(check: Callable[[], None]) -> None:
    try:
        result = check()
        if result is not None:
            if inspect.iscoroutine(result):
                result.close()
            raise TypeError("dispatch guards must return None synchronously")
    except Exception:
        # Caller error text may contain application secrets. Keep it local.
        raise DispatchRejectedError("request dispatch precondition rejected") from None
