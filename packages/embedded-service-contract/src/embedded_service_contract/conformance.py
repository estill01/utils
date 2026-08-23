"""Deterministic assertions for the neutral lifecycle structure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from .contract import (
    Cancelled,
    CancelResult,
    EventRecord,
    Failed,
    HostContract,
    HostShape,
    InvalidCursorError,
    LifecycleHost,
    RunRef,
    RunState,
    RunStatus,
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

    host_factory: Callable[[str], LifecycleHost[RequestT, EventT, ResultT, FailureT]]
    successful_request: RequestT
    failing_request: RequestT
    cancellable_request: RequestT

    def __post_init__(self) -> None:
        if not callable(self.host_factory):
            raise TypeError("host_factory must be callable")


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    """Deterministic non-authoritative summary of checks performed."""

    shape: HostShape
    scenarios: int
    observed_events: int

    def __post_init__(self) -> None:
        if type(self.shape) is not HostShape:
            raise TypeError("shape must be HostShape")
        if type(self.scenarios) is not int or self.scenarios < 0:
            raise ValueError("scenarios must be a non-negative integer")
        if type(self.observed_events) is not int or self.observed_events < 0:
            raise ValueError("observed_events must be a non-negative integer")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConformanceError(message)


def _require_snapshot(
    host: LifecycleHost,
    ref: RunRef,
    status: RunStatus,
    outcome: object,
    events: tuple[EventRecord, ...],
    message: str,
) -> None:
    try:
        unchanged = (
            host.status(ref) == status
            and host.outcome(ref) == outcome
            and host.events(ref) == events
        )
    except Exception as error:
        raise ConformanceError(message) from error
    _require(unchanged, message)


def _events_are_structural(host: LifecycleHost, ref: RunRef, expected_state: RunState) -> int:
    events = host.events(ref)
    _require(type(events) is tuple, "events must be returned as an immutable tuple")
    _require(bool(events), "each reference scenario must publish an event")
    _require(
        all(type(event) is EventRecord for event in events),
        "events must use exact EventRecord envelopes",
    )
    _require(
        [event.sequence for event in events] == list(range(1, len(events) + 1)),
        "event sequences must be contiguous and one-based",
    )
    _require(all(event.ref == ref for event in events), "events must retain their run ref")
    suffix = host.events(ref, after_sequence=1)
    _require(suffix == events[1:], "event cursor must return the exact suffix")
    status = host.status(ref)
    _require(type(status) is RunStatus, "status must use the exact RunStatus value")
    _require(status.ref == ref, "status must retain its requested run ref")
    _require(status.state is expected_state, "status changed outside its structural transition")
    _require(status.last_event_sequence == len(events), "status cursor must match event history")
    return len(events)


def _expect_unknown_ref(host: LifecycleHost, missing: RunRef) -> None:
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


def _expect_unknown(host: LifecycleHost) -> None:
    _expect_unknown_ref(host, RunRef("conformance-missing-run"))


def assert_lifecycle_conformance(
    fixture: ConformanceFixture[RequestT, EventT, ResultT, FailureT],
) -> ConformanceReport:
    """Assert equivalent structure without interpreting caller-owned values."""

    if type(fixture) is not ConformanceFixture:
        raise TypeError("fixture must be ConformanceFixture")
    host = fixture.host_factory("primary")
    if not isinstance(host, LifecycleHost):
        raise ConformanceError("host does not implement the lifecycle protocol")
    if type(host.contract) is not HostContract:
        raise ConformanceError("host must expose the exact validated HostContract value")
    _expect_unknown(host)

    successful = host.start(fixture.successful_request)
    _require(type(successful) is RunRef, "start must return the exact RunRef value")
    successful_outcome = host.outcome(successful)
    _require(type(successful_outcome) is Succeeded, "success outcome is not structural")
    _require(successful_outcome.ref == successful, "success outcome changed its run ref")
    observed = _events_are_structural(host, successful, RunState.SUCCEEDED)
    successful_status = host.status(successful)
    successful_events = host.events(successful)
    successful_cancel = host.cancel(successful)
    _require(type(successful_cancel) is CancelResult, "cancel must use exact CancelResult")
    _require(
        successful_cancel.ref == successful
        and successful_cancel.state is RunState.SUCCEEDED
        and not successful_cancel.changed,
        "cancel changed an already successful run",
    )
    _require_snapshot(
        host,
        successful,
        successful_status,
        successful_outcome,
        successful_events,
        "cancel mutated an already successful run",
    )

    failed = host.start(fixture.failing_request)
    _require(type(failed) is RunRef, "start must return the exact RunRef value")
    failed_outcome = host.outcome(failed)
    _require(type(failed_outcome) is Failed, "failure outcome is not structural")
    _require(failed_outcome.ref == failed, "failure outcome changed its run ref")
    observed += _events_are_structural(host, failed, RunState.FAILED)
    failed_status = host.status(failed)
    failed_events = host.events(failed)
    failed_cancel = host.cancel(failed)
    _require(type(failed_cancel) is CancelResult, "cancel must use exact CancelResult")
    _require(
        failed_cancel.ref == failed
        and failed_cancel.state is RunState.FAILED
        and not failed_cancel.changed,
        "cancel changed an already failed run",
    )
    _require_snapshot(
        host,
        failed,
        failed_status,
        failed_outcome,
        failed_events,
        "cancel mutated an already failed run",
    )

    cancellable = host.start(fixture.cancellable_request)
    _require(type(cancellable) is RunRef, "start must return the exact RunRef value")
    _require(
        len({successful, failed, cancellable}) == 3,
        "one host instance reused a run reference",
    )
    active_status = host.status(cancellable)
    _require(type(active_status) is RunStatus, "status must use the exact RunStatus value")
    _require(active_status.ref == cancellable, "active status changed its run ref")
    _require(active_status.state is RunState.RUNNING, "cancellable run is not active")
    _require(host.outcome(cancellable) is None, "active run published a terminal outcome")
    first_cancel = host.cancel(cancellable)
    _require(type(first_cancel) is CancelResult, "cancel must use exact CancelResult")
    _require(first_cancel.ref == cancellable, "cancel result changed its run ref")
    _require(first_cancel.changed, "first cancellation did not change active state")
    _require(
        first_cancel.state is RunState.CANCELLED,
        "cancellation did not reach terminal state",
    )
    cancelled_outcome = host.outcome(cancellable)
    _require(type(cancelled_outcome) is Cancelled, "cancel outcome is not structural")
    _require(cancelled_outcome.ref == cancellable, "cancel outcome changed its run ref")
    observed += _events_are_structural(host, cancellable, RunState.CANCELLED)
    cancelled_status = host.status(cancellable)
    cancelled_events = host.events(cancellable)

    second_cancel = host.cancel(cancellable)
    _require(type(second_cancel) is CancelResult, "cancel must use exact CancelResult")
    _require(second_cancel.ref == cancellable, "cancel result changed its run ref")
    _require(not second_cancel.changed, "repeated cancellation was not idempotent")
    _require(
        second_cancel.state is RunState.CANCELLED,
        "repeated cancellation did not retain terminal state",
    )
    _require_snapshot(
        host,
        cancellable,
        cancelled_status,
        cancelled_outcome,
        cancelled_events,
        "repeated cancellation mutated the cancelled run",
    )

    probe = host.start(fixture.successful_request)
    _require(type(probe) is RunRef, "probe start must return the exact RunRef value")
    _require(
        probe not in (successful, failed, cancellable),
        "a later start reused a prior run reference",
    )
    _require_snapshot(
        host,
        successful,
        successful_status,
        successful_outcome,
        successful_events,
        "a later start changed the prior successful run",
    )
    _require_snapshot(
        host,
        failed,
        failed_status,
        failed_outcome,
        failed_events,
        "a later start changed the prior failed run",
    )
    _require_snapshot(
        host,
        cancellable,
        cancelled_status,
        cancelled_outcome,
        cancelled_events,
        "a later start changed the prior cancelled run",
    )

    try:
        host.events(cancellable, after_sequence=-1)
    except InvalidCursorError:
        pass
    except Exception as error:
        raise ConformanceError("negative cursor raised the wrong error") from error
    else:
        raise ConformanceError("negative cursor did not fail")

    fresh = fixture.host_factory("fresh")
    _require(fresh is not host, "host factory reused one runtime instance")
    _require(type(fresh.contract) is HostContract, "fresh host contract is not exact")
    _expect_unknown(fresh)
    prior_refs = (successful, failed, cancellable, probe)
    fresh_ref = fresh.start(fixture.successful_request)
    _require(type(fresh_ref) is RunRef, "fresh host start did not return exact RunRef")
    _require(fresh_ref not in prior_refs, "fresh host reused another instance's run ref")
    for prior_ref in prior_refs:
        _expect_unknown_ref(fresh, prior_ref)
    _expect_unknown_ref(host, fresh_ref)
    _require(fresh.contract == host.contract, "fresh host changed its structural contract")
    return ConformanceReport(
        shape=host.contract.shape,
        scenarios=3,
        observed_events=observed,
    )
