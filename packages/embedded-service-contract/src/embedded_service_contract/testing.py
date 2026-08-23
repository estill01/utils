"""Neutral deterministic hosts and failure fixtures for conformance tests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from .conformance import ConformanceFixture
from .contract import (
    Cancelled,
    CancelResult,
    EventRecord,
    Failed,
    HostContract,
    HostShape,
    InvalidCursorError,
    RunRef,
    RunState,
    RunStatus,
    Succeeded,
    UnknownRunError,
)


class ReferenceAction(StrEnum):
    """Test-only action selected by the neutral reference fixture."""

    SUCCEED = "succeed"
    FAIL = "fail"
    WAIT = "wait"


@dataclass(frozen=True, slots=True)
class ReferenceRequest:
    action: ReferenceAction

    def __post_init__(self) -> None:
        if not isinstance(self.action, ReferenceAction):
            raise TypeError("action must be ReferenceAction")


@dataclass(frozen=True, slots=True)
class ReferenceEvent:
    name: str


@dataclass(frozen=True, slots=True)
class ReferenceResult:
    value: str


@dataclass(frozen=True, slots=True)
class ReferenceFailure:
    code: str


ReferenceFixture = ConformanceFixture[
    ReferenceRequest,
    ReferenceEvent,
    ReferenceResult,
    ReferenceFailure,
]


def _validate_lineage(lineage: str) -> str:
    if type(lineage) is not str:
        raise TypeError("lineage must be a string")
    if not lineage or len(lineage) > 128 or any(ord(char) < 32 for char in lineage):
        raise ValueError("lineage must be a bounded non-empty text value")
    return lineage


@dataclass(slots=True)
class _EmbeddedRun:
    state: RunState
    events: list[EventRecord[ReferenceEvent]]
    outcome: Succeeded[ReferenceResult] | Failed[ReferenceFailure] | Cancelled | None


class EmbeddedReferenceHost:
    """Reference host with direct in-object state and no process owner."""

    contract: Final = HostContract(HostShape.EMBEDDED, process_owner_count=0)

    def __init__(self, lineage: str) -> None:
        self._lineage = _validate_lineage(lineage)
        self._next_id = 1
        self._runs: dict[RunRef, _EmbeddedRun] = {}

    def _run(self, ref: RunRef) -> _EmbeddedRun:
        try:
            return self._runs[ref]
        except KeyError:
            raise UnknownRunError("run is unknown to this host") from None

    @staticmethod
    def _append(run: _EmbeddedRun, ref: RunRef, name: str) -> None:
        run.events.append(EventRecord(ref, len(run.events) + 1, ReferenceEvent(name)))

    def start(self, request: ReferenceRequest) -> RunRef:
        if not isinstance(request, ReferenceRequest):
            raise TypeError("request must be ReferenceRequest")
        ref = RunRef(f"embedded-{len(self._lineage)}-{self._lineage}-{self._next_id}")
        self._next_id += 1
        run = _EmbeddedRun(RunState.RUNNING, [], None)
        self._runs[ref] = run
        self._append(run, ref, "started")
        if request.action is ReferenceAction.SUCCEED:
            run.state = RunState.SUCCEEDED
            run.outcome = Succeeded(ref, ReferenceResult("complete"))
            self._append(run, ref, "succeeded")
        elif request.action is ReferenceAction.FAIL:
            run.state = RunState.FAILED
            run.outcome = Failed(ref, ReferenceFailure("fixture-failure"))
            self._append(run, ref, "failed")
        return ref

    def status(self, ref: RunRef) -> RunStatus:
        run = self._run(ref)
        return RunStatus(ref, run.state, len(run.events))

    def events(
        self, ref: RunRef, *, after_sequence: int = 0
    ) -> tuple[EventRecord[ReferenceEvent], ...]:
        if type(after_sequence) is not int or after_sequence < 0:
            raise InvalidCursorError("event cursor must be a non-negative integer")
        return tuple(self._run(ref).events[after_sequence:])

    def cancel(self, ref: RunRef) -> CancelResult:
        run = self._run(ref)
        changed = run.state is RunState.RUNNING
        if changed:
            run.state = RunState.CANCELLED
            run.outcome = Cancelled(ref)
            self._append(run, ref, "cancelled")
        return CancelResult(ref, run.state, changed)

    def outcome(
        self, ref: RunRef
    ) -> Succeeded[ReferenceResult] | Failed[ReferenceFailure] | Cancelled | None:
        return self._run(ref).outcome


class ServiceReferenceHost:
    """Reference host with service-shaped records and one declared owner."""

    contract: Final = HostContract(HostShape.SERVICE, process_owner_count=1)

    def __init__(self, lineage: str) -> None:
        self._lineage = _validate_lineage(lineage)
        self._sequence = 0
        self._records: dict[str, dict[str, object]] = {}

    def _record(self, ref: RunRef) -> dict[str, object]:
        try:
            return self._records[ref.value]
        except KeyError:
            raise UnknownRunError("run is unknown to this host") from None

    @staticmethod
    def _publish(record: dict[str, object], name: str) -> None:
        event_rows = record["events"]
        assert isinstance(event_rows, list)
        event_rows.append({"sequence": len(event_rows) + 1, "name": name})

    def start(self, request: ReferenceRequest) -> RunRef:
        if not isinstance(request, ReferenceRequest):
            raise TypeError("request must be ReferenceRequest")
        self._sequence += 1
        ref = RunRef(f"service-{len(self._lineage)}-{self._lineage}-{self._sequence}")
        row: dict[str, object] = {
            "state": RunState.RUNNING.value,
            "events": [],
            "outcome": None,
        }
        self._records[ref.value] = row
        self._publish(row, "accepted")
        wire_action = request.action.value
        if wire_action == ReferenceAction.SUCCEED.value:
            row["state"] = RunState.SUCCEEDED.value
            row["outcome"] = {"kind": "succeeded", "value": "complete"}
            self._publish(row, "response-ready")
        elif wire_action == ReferenceAction.FAIL.value:
            row["state"] = RunState.FAILED.value
            row["outcome"] = {"kind": "failed", "code": "fixture-failure"}
            self._publish(row, "error-ready")
        return ref

    def status(self, ref: RunRef) -> RunStatus:
        row = self._record(ref)
        event_rows = row["events"]
        assert isinstance(event_rows, list)
        return RunStatus(ref, RunState(str(row["state"])), len(event_rows))

    def events(
        self, ref: RunRef, *, after_sequence: int = 0
    ) -> tuple[EventRecord[ReferenceEvent], ...]:
        if type(after_sequence) is not int or after_sequence < 0:
            raise InvalidCursorError("event cursor must be a non-negative integer")
        rows = self._record(ref)["events"]
        assert isinstance(rows, list)
        return tuple(
            EventRecord(ref, int(row["sequence"]), ReferenceEvent(str(row["name"])))
            for row in rows[after_sequence:]
        )

    def cancel(self, ref: RunRef) -> CancelResult:
        row = self._record(ref)
        state = RunState(str(row["state"]))
        changed = state is RunState.RUNNING
        if changed:
            row["state"] = RunState.CANCELLED.value
            row["outcome"] = {"kind": "cancelled"}
            self._publish(row, "cancel-acknowledged")
            state = RunState.CANCELLED
        return CancelResult(ref, state, changed)

    def outcome(
        self, ref: RunRef
    ) -> Succeeded[ReferenceResult] | Failed[ReferenceFailure] | Cancelled | None:
        row = self._record(ref)
        outcome = row["outcome"]
        if outcome is None:
            return None
        assert isinstance(outcome, dict)
        if outcome["kind"] == "succeeded":
            return Succeeded(ref, ReferenceResult(str(outcome["value"])))
        if outcome["kind"] == "failed":
            return Failed(ref, ReferenceFailure(str(outcome["code"])))
        return Cancelled(ref)


class _OutOfOrderReferenceHost(EmbeddedReferenceHost):
    def events(
        self, ref: RunRef, *, after_sequence: int = 0
    ) -> tuple[EventRecord[ReferenceEvent], ...]:
        events = super().events(ref, after_sequence=after_sequence)
        return tuple(reversed(events))


class _MissingOutcomeReferenceHost:
    contract = HostContract(HostShape.EMBEDDED, process_owner_count=0)

    def __init__(self, lineage: str) -> None:
        self._delegate = EmbeddedReferenceHost(lineage)

    def start(self, request: ReferenceRequest) -> RunRef:
        return self._delegate.start(request)

    def status(self, ref: RunRef) -> RunStatus:
        return self._delegate.status(ref)

    def events(
        self, ref: RunRef, *, after_sequence: int = 0
    ) -> tuple[EventRecord[ReferenceEvent], ...]:
        return self._delegate.events(ref, after_sequence=after_sequence)

    def cancel(self, ref: RunRef) -> CancelResult:
        return self._delegate.cancel(ref)


def embedded_fixture() -> ReferenceFixture:
    return ConformanceFixture(
        host_factory=EmbeddedReferenceHost,
        successful_request=ReferenceRequest(ReferenceAction.SUCCEED),
        failing_request=ReferenceRequest(ReferenceAction.FAIL),
        cancellable_request=ReferenceRequest(ReferenceAction.WAIT),
    )


def service_fixture() -> ReferenceFixture:
    return ConformanceFixture(
        host_factory=ServiceReferenceHost,
        successful_request=ReferenceRequest(ReferenceAction.SUCCEED),
        failing_request=ReferenceRequest(ReferenceAction.FAIL),
        cancellable_request=ReferenceRequest(ReferenceAction.WAIT),
    )


def out_of_order_fixture() -> ReferenceFixture:
    return ConformanceFixture(
        host_factory=_OutOfOrderReferenceHost,
        successful_request=ReferenceRequest(ReferenceAction.SUCCEED),
        failing_request=ReferenceRequest(ReferenceAction.FAIL),
        cancellable_request=ReferenceRequest(ReferenceAction.WAIT),
    )


def missing_operation_fixture() -> ReferenceFixture:
    return ConformanceFixture(
        host_factory=_MissingOutcomeReferenceHost,  # type: ignore[arg-type]
        successful_request=ReferenceRequest(ReferenceAction.SUCCEED),
        failing_request=ReferenceRequest(ReferenceAction.FAIL),
        cancellable_request=ReferenceRequest(ReferenceAction.WAIT),
    )


__all__ = [
    "EmbeddedReferenceHost",
    "ReferenceAction",
    "ReferenceEvent",
    "ReferenceFailure",
    "ReferenceRequest",
    "ReferenceResult",
    "ServiceReferenceHost",
    "embedded_fixture",
    "missing_operation_fixture",
    "out_of_order_fixture",
    "service_fixture",
]
