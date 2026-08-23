"""Closed capability enums for the frozen app-server surface."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RequestCapability(StrEnum):
    THREAD_START = "thread/start"
    THREAD_RESUME = "thread/resume"
    THREAD_READ = "thread/read"
    THREAD_LIST = "thread/list"
    TURN_START = "turn/start"
    TURN_STEER = "turn/steer"
    TURN_INTERRUPT = "turn/interrupt"
    REVIEW_START = "review/start"


class NotificationCapability(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    DEPRECATION_NOTICE = "deprecationNotice"
    THREAD_STARTED = "thread/started"
    THREAD_STATUS_CHANGED = "thread/status/changed"
    THREAD_CLOSED = "thread/closed"
    TURN_STARTED = "turn/started"
    TURN_COMPLETED = "turn/completed"
    TURN_DIFF_UPDATED = "turn/diff/updated"
    TURN_PLAN_UPDATED = "turn/plan/updated"
    ITEM_STARTED = "item/started"
    ITEM_COMPLETED = "item/completed"
    AGENT_MESSAGE_DELTA = "item/agentMessage/delta"
    PLAN_DELTA = "item/plan/delta"
    REASONING_SUMMARY_TEXT_DELTA = "item/reasoning/summaryTextDelta"


class CallbackCapability(StrEnum):
    COMMAND_EXECUTION_APPROVAL = "item/commandExecution/requestApproval"
    FILE_CHANGE_APPROVAL = "item/fileChange/requestApproval"
    USER_INPUT = "item/tool/requestUserInput"


class TransportCapability(StrEnum):
    OWNED_STDIO = "owned-stdio"
    UNIX_SOCKET = "unix-socket"
    INJECTED_BYTE_CHANNEL = "injected-byte-channel"


Capability = RequestCapability | NotificationCapability | CallbackCapability | TransportCapability


@dataclass(frozen=True, slots=True)
class FeatureSet:
    """Exact selected features proven by one compatible schema tree."""

    requests: frozenset[RequestCapability]
    notifications: frozenset[NotificationCapability]
    callbacks: frozenset[CallbackCapability]
    transports: frozenset[TransportCapability]

    def supports(self, capability: Capability) -> bool:
        if isinstance(capability, RequestCapability):
            return capability in self.requests
        if isinstance(capability, NotificationCapability):
            return capability in self.notifications
        if isinstance(capability, CallbackCapability):
            return capability in self.callbacks
        if isinstance(capability, TransportCapability):
            return capability in self.transports
        raise TypeError(f"unsupported capability type: {type(capability).__name__}")
