"""Deterministic in-memory app-server fake for the public conformance matrix."""

from __future__ import annotations

import asyncio
import json
from typing import Final

INITIALIZE_RESULT: Final = {
    "codexHome": "/tmp/codex-home",
    "platformFamily": "unix",
    "platformOs": "macos",
    "userAgent": "codex-app-server-client-conformance",
}

THREAD: Final = {
    "canAcceptDirectInput": None,
    "cliVersion": "0.147.0",
    "createdAt": 0,
    "cwd": "/tmp/conformance",
    "ephemeral": False,
    "historyMode": "full",
    "id": "thread-conformance",
    "modelProvider": "fixture",
    "preview": "fixture",
    "sessionId": "session-conformance",
    "source": "cli",
    "status": {"type": "notLoaded"},
    "turns": [],
    "updatedAt": 0,
}

TURN: Final = {"id": "turn-conformance", "items": [], "status": "completed"}

OPERATION_RESULTS: Final = {
    "thread/start": {
        "approvalPolicy": "untrusted",
        "approvalsReviewer": "user",
        "cwd": "/tmp/conformance",
        "model": "fixture",
        "modelProvider": "fixture",
        "sandbox": {"type": "dangerFullAccess"},
        "thread": THREAD,
    },
    "thread/resume": {
        "approvalPolicy": "untrusted",
        "approvalsReviewer": "user",
        "cwd": "/tmp/conformance",
        "model": "fixture",
        "modelProvider": "fixture",
        "sandbox": {"type": "dangerFullAccess"},
        "thread": THREAD,
    },
    "thread/read": {"thread": THREAD},
    "thread/list": {"data": [THREAD]},
    "turn/start": {"turn": TURN},
    "turn/steer": {"turnId": "turn-conformance"},
    "turn/interrupt": {},
    "review/start": {"reviewThreadId": "review-conformance", "turn": TURN},
}

NOTIFICATION_MATRIX: Final = (
    (
        "error",
        {
            "error": {"message": "fixture"},
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
            "willRetry": False,
        },
        "ErrorNotification",
    ),
    ("warning", {"message": "fixture"}, "WarningNotification"),
    ("deprecationNotice", {"summary": "fixture"}, "DeprecationNoticeNotification"),
    ("thread/started", {"thread": THREAD}, "ThreadStartedNotification"),
    (
        "thread/status/changed",
        {"status": {"type": "notLoaded"}, "threadId": "thread-conformance"},
        "ThreadStatusChangedNotification",
    ),
    ("thread/closed", {"threadId": "thread-conformance"}, "ThreadClosedNotification"),
    ("turn/started", {"threadId": "thread-conformance", "turn": TURN}, "TurnStartedNotification"),
    (
        "turn/completed",
        {"threadId": "thread-conformance", "turn": TURN},
        "TurnCompletedNotification",
    ),
    (
        "turn/diff/updated",
        {"diff": "fixture", "threadId": "thread-conformance", "turnId": "turn-conformance"},
        "TurnDiffUpdatedNotification",
    ),
    (
        "turn/plan/updated",
        {"plan": [], "threadId": "thread-conformance", "turnId": "turn-conformance"},
        "TurnPlanUpdatedNotification",
    ),
    (
        "item/started",
        {
            "item": {"content": [], "id": "item-conformance", "type": "userMessage"},
            "startedAtMs": 0,
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
        },
        "ItemStartedNotification",
    ),
    (
        "item/completed",
        {
            "completedAtMs": 0,
            "item": {"content": [], "id": "item-conformance", "type": "userMessage"},
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
        },
        "ItemCompletedNotification",
    ),
    (
        "item/agentMessage/delta",
        {
            "delta": "fixture",
            "itemId": "item-conformance",
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
        },
        "AgentMessageDeltaNotification",
    ),
    (
        "item/plan/delta",
        {
            "delta": "fixture",
            "itemId": "item-conformance",
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
        },
        "PlanDeltaNotification",
    ),
    (
        "item/reasoning/summaryTextDelta",
        {
            "delta": "fixture",
            "itemId": "item-conformance",
            "summaryIndex": 0,
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
        },
        "ReasoningSummaryTextDeltaNotification",
    ),
)

CALLBACK_MATRIX: Final = (
    (
        "item/commandExecution/requestApproval",
        {
            "itemId": "item-conformance",
            "startedAtMs": 0,
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
        },
        "CommandExecutionApprovalCallback",
        "CommandExecutionRequestApprovalResponse",
        {"decision": "accept"},
    ),
    (
        "item/fileChange/requestApproval",
        {
            "itemId": "item-conformance",
            "startedAtMs": 0,
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
        },
        "FileChangeApprovalCallback",
        "FileChangeRequestApprovalResponse",
        {"decision": "accept"},
    ),
    (
        "item/tool/requestUserInput",
        {
            "isBlocking": False,
            "itemId": "item-conformance",
            "questions": [],
            "threadId": "thread-conformance",
            "turnId": "turn-conformance",
        },
        "UserInputCallback",
        "ToolRequestUserInputResponse",
        {"answers": {}},
    ),
)


class DeterministicAppServer:
    """One exact JSON-lines peer with no filesystem, process, or network effects."""

    def __init__(self) -> None:
        self.incoming: asyncio.Queue[bytes | BaseException] = asyncio.Queue()
        self.writes: list[dict[str, object]] = []
        self.callback_results: list[dict[str, object]] = []
        self.initialized = False
        self.closed = False
        self.closed_event = asyncio.Event()
        self.close_count = 0

    async def read_line(self, *, max_bytes: int) -> bytes:
        value = await self.incoming.get()
        if isinstance(value, BaseException):
            raise value
        if len(value) > max_bytes:
            raise RuntimeError("fixture record exceeded client limit")
        return value

    async def write_line(self, data: bytes) -> None:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise RuntimeError("fixture received a non-object envelope")
        self.writes.append(value)
        method = value.get("method")
        if method == "initialized" and "id" not in value:
            self.initialized = True
            return
        if method == "initialize" and "id" in value:
            self._queue({"id": value["id"], "result": INITIALIZE_RESULT})
            return
        if isinstance(method, str) and "id" in value and method in OPERATION_RESULTS:
            self._queue({"id": value["id"], "result": OPERATION_RESULTS[method]})
            return
        if method is None and "id" in value and ("result" in value or "error" in value):
            self.callback_results.append(value)
            return
        raise RuntimeError("fixture received an unsupported envelope")

    async def close(self) -> None:
        self.close_count += 1
        self.closed = True
        self.closed_event.set()

    def emit_notifications(self) -> None:
        if not self.initialized:
            raise RuntimeError("fixture is not initialized")
        for method, params, _ in NOTIFICATION_MATRIX:
            self._queue({"method": method, "params": params})

    def emit_callback(self, index: int) -> str:
        if not self.initialized:
            raise RuntimeError("fixture is not initialized")
        method, params, _, _, _ = CALLBACK_MATRIX[index]
        request_id = f"callback-{index}"
        self._queue({"id": request_id, "method": method, "params": params})
        return request_id

    def disconnect(self) -> None:
        self.incoming.put_nowait(RuntimeError("fixture disconnected"))

    def _queue(self, value: dict[str, object]) -> None:
        self.incoming.put_nowait(json.dumps(value).encode("utf-8") + b"\n")
