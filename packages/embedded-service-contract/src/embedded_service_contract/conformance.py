"""Deterministic assertions for the neutral lifecycle structure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from .contract import (
    Cancelled,
    Failed,
    HostShape,
    InvalidCursorError,
    LifecycleHost,
    RunRef,
    RunState,
    Succeeded,
    UnknownRunError,
)

RequestT = TypeVar("RequestT")
EventT = TypeVar("EventT")
ResultT = TypeVar("ResultT")
FailureT = TypeVar("FailureT")


class ConformanceError(AssertionError):
    """A host failed the package's structural conformance contract."""


@dataclass(frozen=True, slots=True)
class ConformanceFixture(Generic[RequestT, EventT, ResultT, FailureT]):
    """Caller-supplied requests for three structure-only lifecycle paths."""

    host_factory: Callable[[], LifecycleHost[RequestT, EventT, ResultT, FailureT]]
    successful_request: RequestT
    failing_request: RequestT
    cancellable_request: RequestT


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    """Deterministic non-authoritative summary of checks performed."""

    shape: HostShape
    scenarios: int
    observed_events: int


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConformanceError(message)


def _events_are_structural(host: LifecycleHost, ref: RunRef) -> int:
    events = host.events(ref)
    _require(type(events) is tuple, "events must be returned as an immutable tuple")
    _require(bool(events), "each reference scenario must publish an event")
    _require(
        [event.sequence for event in events] == list(range(1, len(events) + 1)),
        "event sequences must be contiguous and one-based",
    )
    _require(all(event.ref == ref for event in events), "events must retain their run ref")
    suffix = host.events(ref, after_sequence=1)
    _require(suffix == events[1:], "event cursor must return the exact suffix")
    status = host.status(ref)
    _require(status.last_event_sequence == len(events), "status cursor must match event history")
    return len(events)


def _expect_unknown(host: LifecycleHost) -> None:
    missing = RunRef("conformance-missing-run")
    for operation in (
        lambda: host.status(missing),
        lambda: host.events(missing),
        lambda: host.cancel(missing),
        lambda: host.outcome(missing),
    ):
        try:
            operation()
        except UnknownRunError:
            continue
        except Exception as error:
            raise ConformanceError("unknown run raised the wrong error") from error
        raise ConformanceError("unknown run did not raise UnknownRunError")


def assert_lifecycle_conformance(
    fixture: ConformanceFixture[RequestT, EventT, ResultT, FailureT],
) -> ConformanceReport:
    """Assert equivalent structure without interpreting caller-owned values."""

    if not isinstance(fixture, ConformanceFixture):
        raise TypeError("fixture must be ConformanceFixture")
    host = fixture.host_factory()
    if not isinstance(host, LifecycleHost):
        raise ConformanceError("host does not implement the lifecycle protocol")
    if host.contract.schema_version != 1:
        raise ConformanceError("host contract uses an unsupported schema version")
    _expect_unknown(host)

    successful = host.start(fixture.successful_request)
    _require(host.status(successful).state is RunState.SUCCEEDED, "success did not terminate")
    _require(isinstance(host.outcome(successful), Succeeded), "success outcome is not structural")
    observed = _events_are_structural(host, successful)

    failed = host.start(fixture.failing_request)
    _require(host.status(failed).state is RunState.FAILED, "failure did not terminate")
    _require(isinstance(host.outcome(failed), Failed), "failure outcome is not structural")
    observed += _events_are_structural(host, failed)

    cancellable = host.start(fixture.cancellable_request)
    _require(host.status(cancellable).state is RunState.RUNNING, "cancellable run is not active")
    _require(host.outcome(cancellable) is None, "active run published a terminal outcome")
    first_cancel = host.cancel(cancellable)
    second_cancel = host.cancel(cancellable)
    _require(first_cancel.changed, "first cancellation did not change active state")
    _require(not second_cancel.changed, "repeated cancellation was not idempotent")
    _require(
        first_cancel.state is RunState.CANCELLED and second_cancel.state is RunState.CANCELLED,
        "cancellation did not retain terminal state",
    )
    _require(isinstance(host.outcome(cancellable), Cancelled), "cancel outcome is not structural")
    observed += _events_are_structural(host, cancellable)

    try:
        host.events(cancellable, after_sequence=-1)
    except InvalidCursorError:
        pass
    except Exception as error:
        raise ConformanceError("negative cursor raised the wrong error") from error
    else:
        raise ConformanceError("negative cursor did not fail")

    fresh = fixture.host_factory()
    _require(fresh is not host, "host factory reused one runtime instance")
    _expect_unknown(fresh)
    _require(fresh.contract == host.contract, "fresh host changed its structural contract")
    return ConformanceReport(
        shape=host.contract.shape,
        scenarios=3,
        observed_events=observed,
    )
