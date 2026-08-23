"""Neutral structural lifecycle values and host protocol."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, Protocol, TypeAlias, TypeVar, runtime_checkable

RequestT = TypeVar("RequestT", contravariant=True)
EventT = TypeVar("EventT", covariant=True)
ResultT = TypeVar("ResultT", covariant=True)
FailureT = TypeVar("FailureT", covariant=True)


class LifecycleContractError(Exception):
    """Base error for structural lifecycle contract failures."""


class UnknownRunError(LifecycleContractError):
    """The supplied run reference is not owned by this host instance."""


class InvalidCursorError(LifecycleContractError):
    """An event cursor is outside the structural contract."""


class HostShape(StrEnum):
    """The two admitted host composition shapes."""

    EMBEDDED = "embedded"
    SERVICE = "service"


class RunState(StrEnum):
    """Non-authoritative structural lifecycle states."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class HostContract:
    """Describes host shape and explicit process ownership only."""

    shape: HostShape
    process_owner_count: int
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.shape) is not HostShape:
            raise TypeError("shape must be HostShape")
        if type(self.process_owner_count) is not int:
            raise TypeError("process_owner_count must be an integer")
        if self.process_owner_count not in (0, 1):
            raise ValueError("a host composition permits at most one process owner")
        expected = 0 if self.shape is HostShape.EMBEDDED else 1
        if self.process_owner_count != expected:
            raise ValueError("host shape and process ownership disagree")
        if type(self.schema_version) is not int:
            raise TypeError("schema_version must be an integer")
        if self.schema_version != 1:
            raise ValueError("unsupported host-contract schema version")


@dataclass(frozen=True, slots=True)
class RunRef:
    """Opaque host-local run reference."""

    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str:
            raise TypeError("run reference must be a string")
        if not self.value or len(self.value) > 256 or any(ord(char) < 32 for char in self.value):
            raise ValueError("run reference must be a bounded non-empty text value")


@dataclass(frozen=True, slots=True)
class RunStatus:
    """Current structural state and event cursor for one run."""

    ref: RunRef
    state: RunState
    last_event_sequence: int

    def __post_init__(self) -> None:
        if type(self.ref) is not RunRef or type(self.state) is not RunState:
            raise TypeError("status requires exact structural values")
        if type(self.last_event_sequence) is not int or self.last_event_sequence < 0:
            raise ValueError("last_event_sequence must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class EventRecord(Generic[EventT]):
    """Host-local ordered envelope around a caller-owned event value."""

    ref: RunRef
    sequence: int
    value: EventT

    def __post_init__(self) -> None:
        if type(self.ref) is not RunRef:
            raise TypeError("event ref must be RunRef")
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("event sequence must be a positive integer")


@dataclass(frozen=True, slots=True)
class CancelResult:
    """Idempotent structural cancellation observation."""

    ref: RunRef
    state: RunState
    changed: bool

    def __post_init__(self) -> None:
        if type(self.ref) is not RunRef or type(self.state) is not RunState:
            raise TypeError("cancel result requires exact structural values")
        if type(self.changed) is not bool:
            raise TypeError("changed must be boolean")
        if self.changed and self.state is not RunState.CANCELLED:
            raise ValueError("a changed cancellation must end in cancelled state")


@dataclass(frozen=True, slots=True)
class Succeeded(Generic[ResultT]):
    """Caller-owned successful value for a terminal run."""

    ref: RunRef
    value: ResultT

    def __post_init__(self) -> None:
        if type(self.ref) is not RunRef:
            raise TypeError("success ref must be RunRef")


@dataclass(frozen=True, slots=True)
class Failed(Generic[FailureT]):
    """Caller-owned failure value for a terminal run."""

    ref: RunRef
    error: FailureT

    def __post_init__(self) -> None:
        if type(self.ref) is not RunRef:
            raise TypeError("failure ref must be RunRef")


@dataclass(frozen=True, slots=True)
class Cancelled:
    """Structural cancelled outcome with no product meaning."""

    ref: RunRef

    def __post_init__(self) -> None:
        if type(self.ref) is not RunRef:
            raise TypeError("cancelled ref must be RunRef")


RunOutcome: TypeAlias = Succeeded[ResultT] | Failed[FailureT] | Cancelled


@runtime_checkable
class LifecycleHost(Protocol[RequestT, EventT, ResultT, FailureT]):
    """Minimal synchronous structure shared by embedded and service hosts."""

    @property
    def contract(self) -> HostContract: ...

    def start(self, request: RequestT) -> RunRef: ...

    def status(self, ref: RunRef) -> RunStatus: ...

    def events(
        self, ref: RunRef, *, after_sequence: int = 0
    ) -> tuple[EventRecord[EventT], ...]: ...

    def cancel(self, ref: RunRef) -> CancelResult: ...

    def outcome(self, ref: RunRef) -> RunOutcome[ResultT, FailureT] | None: ...
