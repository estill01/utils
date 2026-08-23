"""Bounded typed notification, callback, and termination coordination."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from .errors import (
    AppServerClientError,
    CallbackCapacityError,
    CallCancelledError,
    CorrelationError,
    DisconnectedError,
    JsonRpcValidationError,
    RequestLimitError,
    SessionStateError,
    UnsupportedFeatureError,
)
from .models import (
    AgentMessageDeltaNotification,
    CommandExecutionRequestApprovalParams,
    CommandExecutionRequestApprovalResponse,
    DeprecationNoticeNotification,
    ErrorNotification,
    FileChangeRequestApprovalParams,
    FileChangeRequestApprovalResponse,
    ItemCompletedNotification,
    ItemStartedNotification,
    PlanDeltaNotification,
    ReasoningSummaryTextDeltaNotification,
    ThreadClosedNotification,
    ThreadStartedNotification,
    ThreadStatusChangedNotification,
    ToolRequestUserInputParams,
    ToolRequestUserInputResponse,
    TurnCompletedNotification,
    TurnDiffUpdatedNotification,
    TurnPlanUpdatedNotification,
    TurnStartedNotification,
    WarningNotification,
)
from .surface import CallbackCapability, FeatureSet, NotificationCapability

if TYPE_CHECKING:
    from .rpc import _RpcEngine


ServerEvent: TypeAlias = (
    ErrorNotification
    | WarningNotification
    | DeprecationNoticeNotification
    | ThreadStartedNotification
    | ThreadStatusChangedNotification
    | ThreadClosedNotification
    | TurnStartedNotification
    | TurnCompletedNotification
    | TurnDiffUpdatedNotification
    | TurnPlanUpdatedNotification
    | ItemStartedNotification
    | ItemCompletedNotification
    | AgentMessageDeltaNotification
    | PlanDeltaNotification
    | ReasoningSummaryTextDeltaNotification
)


@dataclass(slots=True)
class _CallbackState:
    owner: _AsyncCoordinator
    request_id: str | int
    method: str
    status: str = "pending"
    failure: AppServerClientError | None = None
    response_task: asyncio.Task[None] | None = None


@dataclass(frozen=True, slots=True, init=False)
class CommandExecutionApprovalCallback:
    """One command approval request whose decision remains caller-owned."""

    params: CommandExecutionRequestApprovalParams
    _state: _CallbackState = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("callbacks are created only by an active session")

    async def respond(self, response: CommandExecutionRequestApprovalResponse) -> None:
        await self._state.owner.respond(
            self._state, response, CommandExecutionRequestApprovalResponse
        )


@dataclass(frozen=True, slots=True, init=False)
class FileChangeApprovalCallback:
    """One file-change approval request whose decision remains caller-owned."""

    params: FileChangeRequestApprovalParams
    _state: _CallbackState = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("callbacks are created only by an active session")

    async def respond(self, response: FileChangeRequestApprovalResponse) -> None:
        await self._state.owner.respond(self._state, response, FileChangeRequestApprovalResponse)


@dataclass(frozen=True, slots=True, init=False)
class UserInputCallback:
    """One user-input request whose answers remain caller-owned."""

    params: ToolRequestUserInputParams
    _state: _CallbackState = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("callbacks are created only by an active session")

    async def respond(self, response: ToolRequestUserInputResponse) -> None:
        await self._state.owner.respond(self._state, response, ToolRequestUserInputResponse)


ServerCallback: TypeAlias = (
    CommandExecutionApprovalCallback | FileChangeApprovalCallback | UserInputCallback
)


_NOTIFICATION_TYPES: Mapping[NotificationCapability, type[ServerEvent]] = {
    NotificationCapability.ERROR: ErrorNotification,
    NotificationCapability.WARNING: WarningNotification,
    NotificationCapability.DEPRECATION_NOTICE: DeprecationNoticeNotification,
    NotificationCapability.THREAD_STARTED: ThreadStartedNotification,
    NotificationCapability.THREAD_STATUS_CHANGED: ThreadStatusChangedNotification,
    NotificationCapability.THREAD_CLOSED: ThreadClosedNotification,
    NotificationCapability.TURN_STARTED: TurnStartedNotification,
    NotificationCapability.TURN_COMPLETED: TurnCompletedNotification,
    NotificationCapability.TURN_DIFF_UPDATED: TurnDiffUpdatedNotification,
    NotificationCapability.TURN_PLAN_UPDATED: TurnPlanUpdatedNotification,
    NotificationCapability.ITEM_STARTED: ItemStartedNotification,
    NotificationCapability.ITEM_COMPLETED: ItemCompletedNotification,
    NotificationCapability.AGENT_MESSAGE_DELTA: AgentMessageDeltaNotification,
    NotificationCapability.PLAN_DELTA: PlanDeltaNotification,
    NotificationCapability.REASONING_SUMMARY_TEXT_DELTA: ReasoningSummaryTextDeltaNotification,
}

_CALLBACK_SPECS: Mapping[
    CallbackCapability, tuple[type[object], type[object], type[ServerCallback]]
] = {
    CallbackCapability.COMMAND_EXECUTION_APPROVAL: (
        CommandExecutionRequestApprovalParams,
        CommandExecutionRequestApprovalResponse,
        CommandExecutionApprovalCallback,
    ),
    CallbackCapability.FILE_CHANGE_APPROVAL: (
        FileChangeRequestApprovalParams,
        FileChangeRequestApprovalResponse,
        FileChangeApprovalCallback,
    ),
    CallbackCapability.USER_INPUT: (
        ToolRequestUserInputParams,
        ToolRequestUserInputResponse,
        UserInputCallback,
    ),
}


def _consume_task_exception(task: asyncio.Task[None]) -> None:
    if not task.cancelled():
        with suppress(Exception):
            task.exception()


def _consume_current_cancellation() -> None:
    task = asyncio.current_task()
    while task is not None and task.cancelling():
        task.uncancel()


def _construct_callback(
    callback_type: type[ServerCallback], params: object, state: _CallbackState
) -> ServerCallback:
    callback = object.__new__(callback_type)
    object.__setattr__(callback, "params", params)
    object.__setattr__(callback, "_state", state)
    return callback


class _AsyncCoordinator:
    """One single-connection coordinator installed before initialization."""

    def __init__(
        self,
        engine: _RpcEngine,
        features: FeatureSet,
        *,
        max_events: int,
        max_callbacks: int,
    ) -> None:
        self._engine = engine
        self._features = features
        self._max_events = max_events
        self._max_callbacks = max_callbacks
        self._events: deque[ServerEvent] = deque()
        self._callbacks: deque[ServerCallback] = deque()
        self._callback_states: dict[str | int, _CallbackState] = {}
        self._event_ready = asyncio.Event()
        self._callback_ready = asyncio.Event()
        self._event_consumer = False
        self._callback_consumer = False
        self._terminated = False
        self._terminal_failure: AppServerClientError | None = None

    def accept_notification(self, method: str, params: object) -> None:
        unselected = False
        try:
            capability = NotificationCapability(method)
        except ValueError:
            unselected = True
        if unselected:
            raise UnsupportedFeatureError("unselected server notification")
        model_type = _NOTIFICATION_TYPES.get(capability)
        if model_type is None or not self._features.supports(capability):
            raise UnsupportedFeatureError("unavailable server notification")
        if self._terminated:
            raise DisconnectedError("server notification arrived after connection termination")
        if len(self._events) >= self._max_events:
            raise RequestLimitError(f"event capacity reached: {self._max_events}")
        event = self._decode(model_type, params, "server notification")
        self._events.append(event)
        self._event_ready.set()

    def accept_callback(self, request_id: str | int, method: str, params: object) -> None:
        unselected = False
        try:
            capability = CallbackCapability(method)
        except ValueError:
            unselected = True
        if unselected:
            raise UnsupportedFeatureError("unselected server callback")
        spec = _CALLBACK_SPECS.get(capability)
        if spec is None or not self._features.supports(capability):
            raise UnsupportedFeatureError("unavailable server callback")
        if self._terminated:
            raise DisconnectedError("server callback arrived after connection termination")
        if request_id in self._callback_states:
            raise CorrelationError("duplicate pending server callback ID")
        if len(self._callback_states) >= self._max_callbacks:
            raise CallbackCapacityError(f"callback capacity reached: {self._max_callbacks}")
        params_type, _, callback_type = spec
        typed_params = self._decode(params_type, params, "server callback")
        state = _CallbackState(owner=self, request_id=request_id, method=method)
        callback = _construct_callback(callback_type, typed_params, state)
        self._callback_states[request_id] = state
        self._callbacks.append(callback)
        self._callback_ready.set()

    @staticmethod
    def _decode(model_type: type[object], value: object, label: str):
        try:
            return model_type.from_dict(value)  # type: ignore[attr-defined, no-any-return]
        except Exception:
            raise JsonRpcValidationError(f"{label} params do not match retained schema") from None

    async def events(self) -> AsyncIterator[ServerEvent]:
        if self._event_consumer:
            raise SessionStateError("only one event iterator may be active")
        self._event_consumer = True
        try:
            while True:
                if self._events:
                    yield self._events.popleft()
                    continue
                if self._terminated:
                    if self._terminal_failure is not None:
                        raise self._terminal_failure
                    return
                self._event_ready.clear()
                if self._events or self._terminated:
                    continue
                await self._event_ready.wait()
        finally:
            self._event_consumer = False

    async def callbacks(self) -> AsyncIterator[ServerCallback]:
        if self._callback_consumer:
            raise SessionStateError("only one callback iterator may be active")
        self._callback_consumer = True
        try:
            while True:
                if self._callbacks:
                    yield self._callbacks.popleft()
                    continue
                if self._terminated:
                    if self._terminal_failure is not None:
                        raise self._terminal_failure
                    return
                self._callback_ready.clear()
                if self._callbacks or self._terminated:
                    continue
                await self._callback_ready.wait()
        finally:
            self._callback_consumer = False

    async def respond(
        self,
        state: _CallbackState,
        response: object,
        expected_response: type[object],
    ) -> None:
        if type(response) is not expected_response:
            raise TypeError("callback response requires its exact frozen response model")
        if state.owner is not self:
            raise SessionStateError("callback belongs to a different coordinator")
        if state.status == "failed" and state.failure is not None:
            raise state.failure
        if state.status != "pending":
            raise CallCancelledError("callback has already selected a terminal result")
        if self._terminated:
            raise self._terminal_failure or CallCancelledError("callback connection is closed")
        try:
            result = response.to_dict()  # type: ignore[attr-defined]
        except Exception:
            raise JsonRpcValidationError("callback response could not be serialized") from None
        line = self._engine._prepare_callback_result(state.request_id, result)
        state.status = "responding"
        state.response_task = asyncio.create_task(self._run_callback_response(state, line))
        state.response_task.add_done_callback(_consume_task_exception)
        try:
            await asyncio.shield(state.response_task)
        except asyncio.CancelledError:
            if state.response_task.done():
                _consume_current_cancellation()
                state.response_task.result()
                return
            _consume_current_cancellation()
            raise CallCancelledError("callback response waiter was cancelled") from None

    async def _run_callback_response(self, state: _CallbackState, line: bytes) -> None:
        try:
            await self._engine._send_prepared_callback_result(line)
        except AppServerClientError as error:
            state.status = "failed"
            state.failure = error
            self._callback_states.pop(state.request_id, None)
            raise
        except Exception:
            failure = DisconnectedError("callback response could not reach the peer")
            state.status = "failed"
            state.failure = failure
            self._callback_states.pop(state.request_id, None)
            raise failure from None
        state.status = "resolved"
        self._callback_states.pop(state.request_id, None)

    def terminate(self, failure: AppServerClientError | None) -> None:
        if self._terminated:
            return
        self._terminated = True
        self._terminal_failure = failure
        callback_failure = failure or CallCancelledError("callback connection closed")
        self._callbacks.clear()
        for state in tuple(self._callback_states.values()):
            if state.status == "pending":
                state.status = "failed"
                state.failure = callback_failure
                self._callback_states.pop(state.request_id, None)
        self._event_ready.set()
        self._callback_ready.set()


__all__ = [
    "CommandExecutionApprovalCallback",
    "FileChangeApprovalCallback",
    "ServerCallback",
    "ServerEvent",
    "UserInputCallback",
]
