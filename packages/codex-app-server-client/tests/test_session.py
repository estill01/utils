from __future__ import annotations

import asyncio
import gc
import inspect
import json
import unittest
import weakref
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

from codex_app_server_client import (
    AppServerClient,
    AppServerSession,
    BinaryIdentity,
    CallbackCapacityError,
    CallCancelledError,
    CallTimeoutError,
    ClientIdentity,
    ClientLimits,
    CommandExecutionApprovalCallback,
    CommandExecutionRequestApprovalResponse,
    CorrelationError,
    DisconnectedError,
    FeatureSet,
    FileChangeApprovalCallback,
    FileChangeRequestApprovalResponse,
    InitializationError,
    InjectedTransport,
    JsonRpcFramingError,
    JsonRpcValidationError,
    MessageTooLargeError,
    NotificationCapability,
    RemoteRpcError,
    RequestCapability,
    RequestLimitError,
    RestartContext,
    RestartError,
    SchemaRootMismatchError,
    SessionStateError,
    StaleGenerationError,
    ToolRequestUserInputResponse,
    TransportCapability,
    TransportCleanupError,
    TransportOwnership,
    UnsupportedFeatureError,
    UserInputCallback,
    inspect_compatibility,
)
from codex_app_server_client.compatibility import _packaged_protocol_root
from codex_app_server_client.models import (
    _PUBLIC_MODEL_NAMES,
    FrozenJsonObject,
    _collect_model_specs,
    _decode,
    _ModelValidationError,
)


def fake_identity() -> BinaryIdentity:
    return BinaryIdentity(
        path=Path("/nonexistent/codex"), reported_version="0.147.0", sha256="0" * 64
    )


def schema_document(name: str) -> dict[str, object]:
    root = _packaged_protocol_root().joinpath("upstream", "0.147.0")
    path = root.joinpath("v2", f"{name}.json")
    if not path.is_file():
        path = root.joinpath(f"{name}.json")
    return json.loads(path.read_text(encoding="utf-8"))


def minimum_value(schema: object, root: dict[str, object]) -> object:
    if schema is True or schema == {}:
        return None
    if schema is False or not isinstance(schema, dict):
        raise AssertionError("fixture encountered a forbidden schema")
    reference = schema.get("$ref")
    if isinstance(reference, str):
        definitions = root["definitions"]
        assert isinstance(definitions, dict)
        return minimum_value(definitions[reference.removeprefix("#/definitions/")], root)
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        return minimum_value(all_of[0], root)
    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        return minimum_value(one_of[0], root)
    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        non_null = [item for item in any_of if item.get("type") != "null"]
        return minimum_value((non_null or any_of)[0], root)
    enum = schema.get("enum")
    if isinstance(enum, list):
        return enum[0]
    expected = schema.get("type")
    if isinstance(expected, list):
        expected = next((item for item in expected if item != "null"), "null")
    if expected == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        assert isinstance(properties, dict)
        return {name: minimum_value(properties[name], root) for name in schema.get("required", [])}
    if expected == "array":
        return []
    if expected == "string":
        return "x"
    if expected in {"integer", "number"}:
        return int(schema.get("minimum", 0))
    if expected == "boolean":
        return False
    if expected == "null":
        return None
    raise AssertionError("fixture encountered an unsupported schema")


def model_fixture(name: str) -> object:
    root = schema_document(name)
    return minimum_value(root, root)


class ScriptedSessionPeer:
    def __init__(self) -> None:
        self.incoming: asyncio.Queue[bytes | BaseException] = asyncio.Queue()
        self.writes: list[dict[str, object]] = []
        self.close_count = 0
        self.close_gate: asyncio.Event | None = None
        self.close_started = asyncio.Event()
        self.close_error: BaseException | None = None
        self.initialize_result: object = {
            "codexHome": "/tmp/codex-home",
            "platformFamily": "unix",
            "platformOs": "macos",
            "userAgent": "fixture",
        }
        self.notification_after_initialized: dict[str, object] | None = None
        self.notifications_before_response: set[str] = set()
        self.result_overrides: dict[str, object] = {}
        self.error_overrides: dict[str, dict[str, object]] = {}
        self.deferred_methods: set[str] = set()
        self.deferred_requests: list[dict[str, object]] = []
        self.callback_response_gate: asyncio.Event | None = None
        self.callback_response_started = asyncio.Event()
        self.request_write_gate: asyncio.Event | None = None
        self.request_write_started = asyncio.Event()
        self.request_write_return_gate: asyncio.Event | None = None
        self.request_response_queued = asyncio.Event()
        self.request_write_returned = asyncio.Event()
        self.initialize_gate: asyncio.Event | None = None
        self.initialize_started = asyncio.Event()
        self.closed = False
        self.responses = {
            operation: model_fixture(response)
            for operation, response in {
                "thread/start": "ThreadStartResponse",
                "thread/resume": "ThreadResumeResponse",
                "thread/read": "ThreadReadResponse",
                "thread/list": "ThreadListResponse",
                "turn/start": "TurnStartResponse",
                "turn/steer": "TurnSteerResponse",
                "turn/interrupt": "TurnInterruptResponse",
                "review/start": "ReviewStartResponse",
            }.items()
        }

    async def read_line(self, *, max_bytes: int) -> bytes:
        value = await self.incoming.get()
        if isinstance(value, BaseException):
            raise value
        return value

    async def write_line(self, data: bytes) -> None:
        value = json.loads(data)
        if (
            self.request_write_gate is not None
            and "id" in value
            and value.get("method") != "initialize"
        ):
            self.request_write_started.set()
            await self.request_write_gate.wait()
            if self.closed:
                raise RuntimeError("peer closed")
        self.writes.append(value)
        if "method" not in value:
            self.callback_response_started.set()
            if self.callback_response_gate is not None:
                await self.callback_response_gate.wait()
            if self.closed:
                raise RuntimeError("peer closed")
            return
        if "id" not in value:
            if value.get("method") == "initialized" and self.notification_after_initialized:
                self._queue_notification(self.notification_after_initialized)
            return
        method = value["method"]
        if method == "initialize" and self.initialize_gate is not None:
            self.initialize_started.set()
            await self.initialize_gate.wait()
            if self.closed:
                raise RuntimeError("peer closed")
        if method in self.deferred_methods:
            self.deferred_requests.append(value)
            return
        result = (
            self.initialize_result
            if method == "initialize"
            else self.result_overrides.get(method, self.responses[method])
        )
        response = (
            {"id": value["id"], "error": self.error_overrides[method]}
            if method in self.error_overrides
            else {"id": value["id"], "result": result}
        )
        if method in self.notifications_before_response:
            self._queue_notification({"method": "warning", "params": {"message": "server-warning"}})
        self.incoming.put_nowait(json.dumps(response).encode("utf-8") + b"\n")
        if method != "initialize":
            self.request_response_queued.set()
            if self.request_write_return_gate is not None:
                await self.request_write_return_gate.wait()
                if self.closed:
                    raise RuntimeError("peer closed")
            self.request_write_returned.set()

    def _queue_notification(self, value: dict[str, object]) -> None:
        self.incoming.put_nowait(json.dumps(value).encode("utf-8") + b"\n")

    def queue_callback(self, request_id: str | int, method: str, params: dict[str, object]) -> None:
        self._queue_notification({"id": request_id, "method": method, "params": params})

    def queue_response(self, request: dict[str, object], result: object) -> None:
        self._queue_notification({"id": request["id"], "result": result})

    def disconnect(self) -> None:
        self.incoming.put_nowait(RuntimeError("private-disconnect-content"))

    async def close(self) -> None:
        self.close_count += 1
        self.closed = True
        self.close_started.set()
        if self.callback_response_gate is not None:
            self.callback_response_gate.set()
        if self.initialize_gate is not None:
            self.initialize_gate.set()
        if self.close_gate is not None:
            await self.close_gate.wait()
        if self.close_error is not None:
            raise self.close_error


class FrozenModelTests(unittest.TestCase):
    def test_selected_top_level_models_round_trip_and_are_frozen(self) -> None:
        import codex_app_server_client.models as models

        for name in _PUBLIC_MODEL_NAMES:
            with self.subTest(name=name):
                value = model_fixture(name)
                model = getattr(models, name).from_dict(value)
                self.assertEqual(model.to_dict(), value)
        identity = ClientIdentity("fixture", "1.0", "Fixture")
        self.assertEqual(
            identity.to_dict(), {"name": "fixture", "version": "1.0", "title": "Fixture"}
        )
        self.assertEqual(
            str(inspect.signature(ClientIdentity)),
            "(name: 'str', version: 'str', title: 'str | None' = None) -> None",
        )
        with self.assertRaises(FrozenInstanceError):
            identity.name = "changed"  # type: ignore[misc]

    def test_arrays_and_open_json_are_deeply_immutable(self) -> None:
        import codex_app_server_client.models as models

        params = models.ThreadStartParams(config={"nested": [1, {"ok": True}]})
        self.assertIsInstance(params.config, FrozenJsonObject)
        self.assertEqual(params.config["nested"][0], 1)  # type: ignore[index]
        self.assertIsInstance(params.config["nested"], tuple)
        self.assertEqual(params.to_dict(), {"config": {"nested": [1, {"ok": True}]}})
        with self.assertRaises(_ModelValidationError):
            models.ThreadReadParams.from_dict({"threadId": "x", "unselected": True})

    def test_same_name_unequal_schema_fails_closed(self) -> None:
        first = {"title": "Conflict", "type": "object", "properties": {"a": {"type": "string"}}}
        second = {"title": "Conflict", "type": "object", "properties": {"b": {"type": "string"}}}
        with self.assertRaises(_ModelValidationError):
            _collect_model_specs({"first.json": first, "second.json": second})

    def test_every_retained_integer_format_enforces_its_exact_range(self) -> None:
        bounds = {
            "int32": (-(2**31), 2**31 - 1),
            "int64": (-(2**63), 2**63 - 1),
            "uint": (0, 2**64 - 1),
            "uint16": (0, 2**16 - 1),
            "uint32": (0, 2**32 - 1),
            "uint64": (0, 2**64 - 1),
        }
        for integer_format, (lower, upper) in bounds.items():
            schema = {"type": "integer", "format": integer_format}
            with self.subTest(integer_format=integer_format):
                self.assertEqual(_decode(schema, {}, lower, "integer"), lower)
                self.assertEqual(_decode(schema, {}, upper, "integer"), upper)
                with self.assertRaises(_ModelValidationError):
                    _decode(schema, {}, lower - 1, "integer")
                with self.assertRaises(_ModelValidationError):
                    _decode(schema, {}, upper + 1, "integer")

    def test_event_and_callback_models_reject_formatted_integer_overflow(self) -> None:
        import codex_app_server_client as client_api

        cases = (
            ("ItemStartedNotification", "startedAtMs", 2**63),
            ("ReasoningSummaryTextDeltaNotification", "summaryIndex", 2**63),
            ("FileChangeRequestApprovalParams", "startedAtMs", 2**63),
            ("ToolRequestUserInputParams", "autoResolutionMs", 2**64),
        )
        for model_name, field_name, overflow in cases:
            with self.subTest(model=model_name, field=field_name):
                value = model_fixture(model_name)
                assert isinstance(value, dict)
                value[field_name] = overflow
                with self.assertRaises(_ModelValidationError) as raised:
                    getattr(client_api, model_name).from_dict(value)
                self.assertNotIn(str(overflow), str(raised.exception))


class TypedSessionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compatibility = inspect_compatibility(fake_identity())

    async def connect(self, peer: ScriptedSessionPeer, *, compatibility: Any = None):
        transport = InjectedTransport(peer, ownership=TransportOwnership.OWNED)
        return await AppServerClient.connect(
            transport,
            self.compatibility if compatibility is None else compatibility,
        )

    async def initialize(self, peer: ScriptedSessionPeer, *, compatibility: Any = None):
        client = await self.connect(peer, compatibility=compatibility)
        session = await client.initialize(ClientIdentity("fixture", "1.0"))
        return client, session

    async def test_handshake_is_exact_once_and_negotiates_closed_features(self) -> None:
        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        self.assertEqual([write["method"] for write in peer.writes], ["initialize", "initialized"])
        params = peer.writes[0]["params"]
        capabilities = params["capabilities"]
        self.assertFalse(capabilities["experimentalApi"])
        self.assertEqual(capabilities["extensions"], {})
        self.assertFalse(capabilities["mcpServerOpenaiFormElicitation"])
        self.assertFalse(capabilities["requestAttestation"])
        selected = {item.value for item in NotificationCapability}
        opted_out = set(capabilities["optOutNotificationMethods"])
        self.assertEqual(len(opted_out), 55)
        self.assertTrue(selected.isdisjoint(opted_out))
        self.assertEqual(len(selected | opted_out), 70)
        self.assertEqual(session.generation, 1)
        self.assertEqual(client._engine._generation, 1)
        self.assertEqual(client._coordinator._generation, 1)
        self.assertEqual(
            session.capabilities.transports,
            frozenset({TransportCapability.INJECTED_BYTE_CHANNEL}),
        )
        self.assertTrue(all(session.capabilities.supports(item) for item in RequestCapability))
        self.assertEqual(session.capabilities.notifications, frozenset(NotificationCapability))
        self.assertEqual(
            {item.value for item in session.capabilities.callbacks},
            {
                "item/commandExecution/requestApproval",
                "item/fileChange/requestApproval",
                "item/tool/requestUserInput",
            },
        )
        with self.assertRaises(SessionStateError):
            await client.initialize(ClientIdentity("fixture", "1.0"))
        with self.assertRaises(SessionStateError):
            await client.initialize(ClientIdentity("changed", "2.0"))
        await session.close()
        self.assertEqual(peer.close_count, 1)

    async def test_unselected_notification_before_request_fails_closed(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.notification_after_initialized = {
            "method": "account/updated",
            "params": {},
        }
        client, session = await self.initialize(peer)
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        with self.assertRaises(SessionStateError):
            await session.read_thread(client_api.ThreadReadParams(threadId="x"))
        self.assertEqual(client._state, "failed")
        self.assertEqual([write["method"] for write in peer.writes], ["initialize", "initialized"])
        self.assertEqual(peer.close_count, 1)

    async def test_unselected_notification_between_request_and_response_fails_closed(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.notifications_before_response.add("thread/read")
        original_queue = peer._queue_notification

        def queue_unselected(_: dict[str, object]) -> None:
            original_queue({"method": "account/updated", "params": {}})

        peer._queue_notification = queue_unselected  # type: ignore[method-assign]
        client, session = await self.initialize(peer)
        with self.assertRaises(UnsupportedFeatureError):
            await session.read_thread(client_api.ThreadReadParams(threadId="x"))
        self.assertEqual(client._state, "failed")
        self.assertEqual(peer.writes[-1]["method"], "thread/read")
        self.assertEqual(peer.close_count, 1)
        with self.assertRaises(SessionStateError):
            await session.read_thread(client_api.ThreadReadParams(threadId="x"))

    async def test_all_eight_operations_are_exactly_typed_and_validated(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        operations = (
            ("start_thread", "thread/start", "ThreadStartParams", "ThreadStartResponse"),
            ("resume_thread", "thread/resume", "ThreadResumeParams", "ThreadResumeResponse"),
            ("read_thread", "thread/read", "ThreadReadParams", "ThreadReadResponse"),
            ("list_threads", "thread/list", "ThreadListParams", "ThreadListResponse"),
            ("start_turn", "turn/start", "TurnStartParams", "TurnStartResponse"),
            ("steer_turn", "turn/steer", "TurnSteerParams", "TurnSteerResponse"),
            (
                "interrupt_turn",
                "turn/interrupt",
                "TurnInterruptParams",
                "TurnInterruptResponse",
            ),
            ("start_review", "review/start", "ReviewStartParams", "ReviewStartResponse"),
        )
        for operation, method, params_name, response_name in operations:
            with self.subTest(method=method):
                params_type = getattr(client_api, params_name)
                params = params_type.from_dict(model_fixture(params_name))
                response = await getattr(session, operation)(params)
                self.assertIsInstance(response, getattr(client_api, response_name))
                self.assertEqual(peer.writes[-1]["method"], method)
                self.assertEqual(peer.writes[-1]["params"], params.to_dict())
        await session.close()

    async def test_invalid_initialize_result_fails_closed_and_is_content_free(self) -> None:
        peer = ScriptedSessionPeer()
        peer.initialize_result = {"private": "initialize-content"}
        client = await self.connect(peer)
        with self.assertRaises(InitializationError) as raised:
            await client.initialize(ClientIdentity("fixture", "1.0"))
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        self.assertNotIn("private", repr(vars(raised.exception)))
        self.assertEqual([write["method"] for write in peer.writes], ["initialize"])
        self.assertEqual(peer.close_count, 1)
        with self.assertRaises(SessionStateError):
            await client.initialize(ClientIdentity("fixture", "1.0"))

    async def test_method_gate_rejects_before_write(self) -> None:
        peer = ScriptedSessionPeer()
        features = self.compatibility.features
        compatibility = replace(
            self.compatibility,
            features=FeatureSet(
                requests=features.requests - {RequestCapability.THREAD_READ},
                notifications=features.notifications,
                callbacks=features.callbacks,
                transports=features.transports,
            ),
        )
        _, session = await self.initialize(peer, compatibility=compatibility)
        before = len(peer.writes)
        params_type = __import__(
            "codex_app_server_client", fromlist=["ThreadReadParams"]
        ).ThreadReadParams
        with self.assertRaises(UnsupportedFeatureError):
            await session.read_thread(params_type(threadId="x"))
        self.assertEqual(len(peer.writes), before)
        await session.close()

    async def test_unavailable_selected_notification_is_opted_out(self) -> None:
        peer = ScriptedSessionPeer()
        features = self.compatibility.features
        compatibility = replace(
            self.compatibility,
            features=FeatureSet(
                requests=features.requests,
                notifications=features.notifications - {NotificationCapability.WARNING},
                callbacks=features.callbacks,
                transports=features.transports,
            ),
        )
        _, session = await self.initialize(peer, compatibility=compatibility)
        optouts = peer.writes[0]["params"]["capabilities"]["optOutNotificationMethods"]
        self.assertIn("warning", optouts)
        self.assertEqual(len(optouts), 56)
        self.assertFalse(session.capabilities.supports(NotificationCapability.WARNING))
        await session.close()

    async def test_incompatible_inputs_fail_before_transport_claim(self) -> None:
        wrong_schema = replace(
            self.compatibility,
            semantic_schema_root_sha256="f" * 64,
        )
        schema_peer = ScriptedSessionPeer()
        with self.assertRaises(SchemaRootMismatchError):
            await self.connect(schema_peer, compatibility=wrong_schema)
        self.assertEqual(schema_peer.writes, [])
        self.assertEqual(schema_peer.close_count, 0)

        features = self.compatibility.features
        wrong_transport = replace(
            self.compatibility,
            features=FeatureSet(
                requests=features.requests,
                notifications=features.notifications,
                callbacks=features.callbacks,
                transports=features.transports - {TransportCapability.INJECTED_BYTE_CHANNEL},
            ),
        )
        transport_peer = ScriptedSessionPeer()
        with self.assertRaises(UnsupportedFeatureError):
            await self.connect(transport_peer, compatibility=wrong_transport)
        self.assertEqual(transport_peer.writes, [])
        self.assertEqual(transport_peer.close_count, 0)

    async def test_invalid_operation_result_invalidates_session_without_content_leak(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.result_overrides["turn/steer"] = {"private": "result-content"}
        _, session = await self.initialize(peer)
        params = client_api.TurnSteerParams.from_dict(model_fixture("TurnSteerParams"))
        with self.assertRaises(JsonRpcValidationError) as raised:
            await session.steer_turn(params)
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        self.assertNotIn("private", repr(vars(raised.exception)))
        with self.assertRaises(SessionStateError):
            await session.interrupt_turn(client_api.TurnInterruptParams(threadId="x", turnId="x"))
        self.assertEqual(peer.close_count, 1)

    async def test_no_raw_escape_wrong_model_and_post_close_reject(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        self.assertFalse(any(hasattr(client, name) for name in ("call", "request", "raw_rpc")))
        self.assertFalse(any(hasattr(session, name) for name in ("call", "request", "raw_rpc")))
        with self.assertRaises(TypeError):
            await session.read_thread({"threadId": "x"})  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            AppServerSession(client, session.capabilities)  # type: ignore[call-arg]
        await client.close()
        with self.assertRaises(SessionStateError):
            await session.read_thread(client_api.ThreadReadParams(threadId="x"))

    async def test_cancelled_close_continues_once_and_retry_observes_cleanup(self) -> None:
        peer = ScriptedSessionPeer()
        peer.close_gate = asyncio.Event()
        _, session = await self.initialize(peer)
        first = asyncio.create_task(session.close())
        await peer.close_started.wait()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        retry = asyncio.create_task(session.close())
        await asyncio.sleep(0)
        self.assertFalse(retry.done())
        peer.close_gate.set()
        await retry
        self.assertEqual(peer.close_count, 1)

    async def test_cleanup_failure_is_typed_retrievable_and_content_free(self) -> None:
        peer = ScriptedSessionPeer()
        peer.close_error = RuntimeError("private-cleanup-content")
        _, session = await self.initialize(peer)
        with self.assertRaises(TransportCleanupError) as first:
            await session.close()
        self.assertIsNone(first.exception.__cause__)
        self.assertIsNone(first.exception.__context__)
        self.assertNotIn("private", repr(vars(first.exception)))
        with self.assertRaises(TransportCleanupError):
            await session.close()
        self.assertEqual(peer.close_count, 1)

    async def test_invalid_result_cancelled_during_cleanup_rejoins_on_close(self) -> None:
        import codex_app_server_client as client_api

        for cleanup_fails in (False, True):
            with self.subTest(cleanup_fails=cleanup_fails):
                peer = ScriptedSessionPeer()
                peer.close_gate = asyncio.Event()
                if cleanup_fails:
                    peer.close_error = RuntimeError("private-cleanup-content")
                peer.result_overrides["thread/read"] = {"invalid": True}
                _, session = await self.initialize(peer)
                operation = asyncio.create_task(
                    session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                )
                await peer.close_started.wait()
                operation.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await operation
                retry = asyncio.create_task(session.close())
                await asyncio.sleep(0)
                self.assertFalse(retry.done())
                peer.close_gate.set()
                if cleanup_fails:
                    with self.assertRaises(TransportCleanupError) as raised:
                        await retry
                    self.assertNotIn("private", repr(vars(raised.exception)))
                else:
                    await retry
                self.assertEqual(peer.close_count, 1)


class AsyncCoordinationTests(unittest.IsolatedAsyncioTestCase):
    NOTIFICATIONS = (
        ("error", "ErrorNotification"),
        ("warning", "WarningNotification"),
        ("deprecationNotice", "DeprecationNoticeNotification"),
        ("thread/started", "ThreadStartedNotification"),
        ("thread/status/changed", "ThreadStatusChangedNotification"),
        ("thread/closed", "ThreadClosedNotification"),
        ("turn/started", "TurnStartedNotification"),
        ("turn/completed", "TurnCompletedNotification"),
        ("turn/diff/updated", "TurnDiffUpdatedNotification"),
        ("turn/plan/updated", "TurnPlanUpdatedNotification"),
        ("item/started", "ItemStartedNotification"),
        ("item/completed", "ItemCompletedNotification"),
        ("item/agentMessage/delta", "AgentMessageDeltaNotification"),
        ("item/plan/delta", "PlanDeltaNotification"),
        (
            "item/reasoning/summaryTextDelta",
            "ReasoningSummaryTextDeltaNotification",
        ),
    )
    CALLBACKS = (
        (
            "callback-string",
            "item/commandExecution/requestApproval",
            "CommandExecutionRequestApprovalParams",
            CommandExecutionApprovalCallback,
            "CommandExecutionRequestApprovalResponse",
            CommandExecutionRequestApprovalResponse,
        ),
        (
            -1,
            "item/fileChange/requestApproval",
            "FileChangeRequestApprovalParams",
            FileChangeApprovalCallback,
            "FileChangeRequestApprovalResponse",
            FileChangeRequestApprovalResponse,
        ),
        (
            -(2**63),
            "item/tool/requestUserInput",
            "ToolRequestUserInputParams",
            UserInputCallback,
            "ToolRequestUserInputResponse",
            ToolRequestUserInputResponse,
        ),
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.compatibility = inspect_compatibility(fake_identity())

    async def initialize(self, peer: ScriptedSessionPeer, *, limits: ClientLimits | None = None):
        client = await AppServerClient.connect(
            InjectedTransport(peer, ownership=TransportOwnership.OWNED),
            self.compatibility,
            limits=limits or ClientLimits(),
        )
        session = await client.initialize(ClientIdentity("fixture", "1.0"))
        return client, session

    @staticmethod
    async def wait_for_deferred(peer: ScriptedSessionPeer) -> dict[str, object]:
        for _ in range(100):
            if peer.deferred_requests:
                return peer.deferred_requests[-1]
            await asyncio.sleep(0)
        raise AssertionError("request was not deferred")

    async def test_all_selected_notifications_project_once_in_order(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        for method, model_name in self.NOTIFICATIONS:
            params = model_fixture(model_name)
            assert isinstance(params, dict)
            peer._queue_notification({"method": method, "params": params})
        iterator = session.events()
        events = [await asyncio.wait_for(anext(iterator), 1.0) for _ in self.NOTIFICATIONS]
        self.assertEqual(
            [type(event).__name__ for event in events],
            [model_name for _, model_name in self.NOTIFICATIONS],
        )
        await iterator.aclose()
        await session.close()

    async def test_notification_interleaves_with_typed_response_without_corruption(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.notifications_before_response.add("thread/read")
        _, session = await self.initialize(peer)
        operation = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        )
        event = await asyncio.wait_for(anext(session.events()), 1.0)
        result = await operation
        self.assertEqual(type(event).__name__, "WarningNotification")
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        await session.close()

    async def test_event_capacity_fails_closed_without_dropping_queued_event(self) -> None:
        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer, limits=ClientLimits(max_events=1))
        for message in ("first", "overflow"):
            peer._queue_notification({"method": "warning", "params": {"message": message}})
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        iterator = session.events()
        first = await anext(iterator)
        self.assertEqual(first.message, "first")
        with self.assertRaises(RequestLimitError):
            await anext(iterator)
        self.assertEqual(peer.close_count, 1)

    async def test_malformed_selected_notification_is_content_free_and_terminal(self) -> None:
        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        peer._queue_notification(
            {"method": "warning", "params": {"private": "notification-content"}}
        )
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        with self.assertRaises(JsonRpcValidationError) as raised:
            await anext(session.events())
        self.assertNotIn("private", str(raised.exception))
        self.assertNotIn("notification-content", repr(vars(raised.exception)))

    async def test_composed_transport_preserves_framing_and_size_failures(self) -> None:
        cases = (
            (b"x" * 65_536 + b"\n", MessageTooLargeError),
            (b"{}", JsonRpcFramingError),
        )
        for line, expected_error in cases:
            with self.subTest(expected_error=expected_error.__name__):
                peer = ScriptedSessionPeer()
                client, session = await self.initialize(
                    peer, limits=ClientLimits(max_message_bytes=65_536)
                )
                peer.incoming.put_nowait(line)
                await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                with self.assertRaises(expected_error):
                    await anext(session.events())
                self.assertEqual(peer.close_count, 1)

    async def test_non_utf8_and_bom_records_fail_before_publication(self) -> None:
        import codex_app_server_client as client_api

        encodings = (
            ("utf-16-le", lambda text: text.encode("utf-16-le")),
            ("utf-16-be", lambda text: text.encode("utf-16-be")),
            ("utf-32-le", lambda text: text.encode("utf-32-le")),
            ("utf-32-be", lambda text: text.encode("utf-32-be")),
            ("utf-8-bom", lambda text: b"\xef\xbb\xbf" + text.encode("utf-8")),
        )
        envelope_kinds = ("response", "event", "callback")
        for encoding, encode in encodings:
            for envelope_kind in envelope_kinds:
                with self.subTest(encoding=encoding, envelope_kind=envelope_kind):
                    peer = ScriptedSessionPeer()
                    peer.deferred_methods.add("thread/read")
                    client, session = await self.initialize(peer)
                    operation = asyncio.create_task(
                        session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                    )
                    request = await self.wait_for_deferred(peer)
                    if envelope_kind == "response":
                        envelope = {
                            "id": request["id"],
                            "result": model_fixture("ThreadReadResponse"),
                            "privateMarker": "private-encoding-content",
                        }
                    elif envelope_kind == "event":
                        envelope = {
                            "method": "warning",
                            "params": {
                                "message": "private-encoding-content",
                            },
                        }
                    else:
                        params = model_fixture("CommandExecutionRequestApprovalParams")
                        assert isinstance(params, dict)
                        params["privateMarker"] = "private-encoding-content"
                        envelope = {
                            "id": "private-encoding-content",
                            "method": "item/commandExecution/requestApproval",
                            "params": params,
                        }
                    text = json.dumps(envelope, separators=(",", ":"))
                    peer.incoming.put_nowait(encode(text) + b"\n")
                    await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                    with self.assertRaises(JsonRpcFramingError) as raised:
                        await operation
                    self.assertNotIn("private-encoding-content", str(raised.exception))
                    self.assertNotIn("private-encoding-content", repr(vars(raised.exception)))
                    with self.assertRaises(JsonRpcFramingError):
                        await anext(session.events())
                    with self.assertRaises(JsonRpcFramingError):
                        await anext(session.callbacks())
                    self.assertEqual(len(client._coordinator._events), 0)
                    self.assertEqual(len(client._coordinator._callbacks), 0)
                    self.assertEqual(len(client._coordinator._callback_states), 0)
                    self.assertEqual(
                        sum("result" in write for write in peer.writes),
                        0,
                    )

    async def test_formatted_integer_overflow_in_notification_fails_closed(self) -> None:
        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        params = model_fixture("ItemStartedNotification")
        assert isinstance(params, dict)
        params["startedAtMs"] = 2**63
        peer._queue_notification({"method": "item/started", "params": params})
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        with self.assertRaises(JsonRpcValidationError) as raised:
            await anext(session.events())
        self.assertNotIn(str(2**63), str(raised.exception))

    async def test_formatted_integer_overflow_in_callbacks_fails_closed(self) -> None:
        cases = (
            (
                "item/fileChange/requestApproval",
                "FileChangeRequestApprovalParams",
                "startedAtMs",
                2**63,
            ),
            (
                "item/tool/requestUserInput",
                "ToolRequestUserInputParams",
                "autoResolutionMs",
                2**64,
            ),
        )
        for method, model_name, field_name, overflow in cases:
            with self.subTest(method=method):
                peer = ScriptedSessionPeer()
                client, session = await self.initialize(peer)
                params = model_fixture(model_name)
                assert isinstance(params, dict)
                params[field_name] = overflow
                peer.queue_callback("overflow", method, params)
                await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                with self.assertRaises(JsonRpcValidationError) as raised:
                    await anext(session.callbacks())
                self.assertNotIn(str(overflow), str(raised.exception))

    async def test_lone_surrogate_callback_id_is_rejected_before_publication(self) -> None:
        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer, limits=ClientLimits(max_callbacks=1))
        params = model_fixture("FileChangeRequestApprovalParams")
        assert isinstance(params, dict)
        peer.queue_callback("\ud800", "item/fileChange/requestApproval", params)
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        with self.assertRaises(JsonRpcFramingError):
            await anext(session.callbacks())
        self.assertEqual(len(client._coordinator._callback_states), 0)
        self.assertEqual(
            sum("result" in write for write in peer.writes),
            0,
        )

    async def test_lone_surrogate_notification_value_and_key_fail_before_queueing(
        self,
    ) -> None:
        cases = (
            {"method": "warning", "params": {"message": "\ud800"}},
            {
                "method": "warning",
                "params": {"message": "safe", "\ud800": "value"},
            },
        )
        for notification in cases:
            with self.subTest(notification_keys=tuple(notification["params"])):
                peer = ScriptedSessionPeer()
                client, session = await self.initialize(peer)
                peer._queue_notification(notification)
                await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                with self.assertRaises(JsonRpcFramingError):
                    await anext(session.events())
                self.assertEqual(len(client._coordinator._events), 0)

    async def test_all_callback_families_echo_string_and_signed_int64_ids(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        for request_id, method, params_name, _, _, _ in self.CALLBACKS:
            params = model_fixture(params_name)
            assert isinstance(params, dict)
            peer.queue_callback(request_id, method, params)
        iterator = session.callbacks()
        for request_id, _, _, callback_type, response_name, response_type in self.CALLBACKS:
            callback = await asyncio.wait_for(anext(iterator), 1.0)
            self.assertIsInstance(callback, callback_type)
            response_value = model_fixture(response_name)
            assert isinstance(response_value, dict)
            response = response_type.from_dict(response_value)
            await callback.respond(response)
            self.assertEqual(peer.writes[-1], {"id": request_id, "result": response_value})
        await iterator.aclose()
        await session.close()

    async def test_callback_response_is_exact_type_and_exactly_once(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        params = model_fixture("CommandExecutionRequestApprovalParams")
        assert isinstance(params, dict)
        peer.queue_callback("approval", "item/commandExecution/requestApproval", params)
        callback = await anext(session.callbacks())
        wrong_value = model_fixture("FileChangeRequestApprovalResponse")
        assert isinstance(wrong_value, dict)
        with self.assertRaises(TypeError):
            await callback.respond(FileChangeRequestApprovalResponse.from_dict(wrong_value))
        response_value = model_fixture("CommandExecutionRequestApprovalResponse")
        assert isinstance(response_value, dict)
        response = CommandExecutionRequestApprovalResponse.from_dict(response_value)
        await callback.respond(response)
        with self.assertRaises(CallCancelledError):
            await callback.respond(response)
        self.assertEqual(
            sum(write.get("id") == "approval" and "result" in write for write in peer.writes),
            1,
        )
        await session.close()

    async def test_selected_callback_success_wins_outer_waiter_cancellation(self) -> None:
        peer = ScriptedSessionPeer()
        peer.callback_response_gate = asyncio.Event()
        _, session = await self.initialize(peer)
        params = model_fixture("CommandExecutionRequestApprovalParams")
        response_value = model_fixture("CommandExecutionRequestApprovalResponse")
        assert isinstance(params, dict)
        assert isinstance(response_value, dict)
        peer.queue_callback("approval", "item/commandExecution/requestApproval", params)
        callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
        response = CommandExecutionRequestApprovalResponse.from_dict(response_value)
        waiter = asyncio.create_task(callback.respond(response))
        await peer.callback_response_started.wait()
        response_task = callback._state.response_task
        assert response_task is not None

        def cancel_waiter_twice(_task: asyncio.Task[None]) -> None:
            waiter.cancel()
            waiter.cancel()

        response_task.add_done_callback(cancel_waiter_twice)
        peer.callback_response_gate.set()
        await waiter
        self.assertEqual(waiter.cancelling(), 0)
        self.assertEqual(callback._state.status, "resolved")
        await session.close()

    async def test_selected_callback_write_failure_wins_outer_waiter_cancellation(self) -> None:
        peer = ScriptedSessionPeer()
        peer.callback_response_gate = asyncio.Event()
        _, session = await self.initialize(peer)
        params = model_fixture("CommandExecutionRequestApprovalParams")
        response_value = model_fixture("CommandExecutionRequestApprovalResponse")
        assert isinstance(params, dict)
        assert isinstance(response_value, dict)
        peer.queue_callback("approval", "item/commandExecution/requestApproval", params)
        callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
        response = CommandExecutionRequestApprovalResponse.from_dict(response_value)
        waiter = asyncio.create_task(callback.respond(response))
        await peer.callback_response_started.wait()
        response_task = callback._state.response_task
        assert response_task is not None

        def cancel_waiter_twice(_task: asyncio.Task[None]) -> None:
            waiter.cancel()
            waiter.cancel()

        response_task.add_done_callback(cancel_waiter_twice)
        peer.closed = True
        peer.callback_response_gate.set()
        with self.assertRaises(DisconnectedError):
            await waiter
        self.assertEqual(waiter.cancelling(), 0)
        self.assertEqual(callback._state.status, "failed")

    async def test_callback_envelopes_are_privately_constructed(self) -> None:
        for callback_type in (
            CommandExecutionApprovalCallback,
            FileChangeApprovalCallback,
            UserInputCallback,
        ):
            with (
                self.subTest(callback=callback_type.__name__),
                self.assertRaises(TypeError),
            ):
                callback_type()  # type: ignore[call-arg]

    async def test_concurrent_callback_response_claim_produces_one_write(self) -> None:
        peer = ScriptedSessionPeer()
        peer.callback_response_gate = asyncio.Event()
        _, session = await self.initialize(peer)
        params = model_fixture("FileChangeRequestApprovalParams")
        assert isinstance(params, dict)
        peer.queue_callback("approval", "item/fileChange/requestApproval", params)
        callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
        response_value = model_fixture("FileChangeRequestApprovalResponse")
        assert isinstance(response_value, dict)
        response = FileChangeRequestApprovalResponse.from_dict(response_value)
        first = asyncio.create_task(callback.respond(response))
        await peer.callback_response_started.wait()
        with self.assertRaises(CallCancelledError):
            await callback.respond(response)
        peer.callback_response_gate.set()
        await first
        self.assertEqual(
            sum(write.get("id") == "approval" and "result" in write for write in peer.writes),
            1,
        )
        await session.close()

    async def test_callback_capacity_releases_only_after_terminal_response(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer, limits=ClientLimits(max_callbacks=1))
        params = model_fixture("FileChangeRequestApprovalParams")
        response_value = model_fixture("FileChangeRequestApprovalResponse")
        assert isinstance(params, dict)
        assert isinstance(response_value, dict)
        iterator = session.callbacks()
        peer.queue_callback(1, "item/fileChange/requestApproval", params)
        first = await asyncio.wait_for(anext(iterator), 1.0)
        await first.respond(FileChangeRequestApprovalResponse.from_dict(response_value))
        peer.queue_callback(2, "item/fileChange/requestApproval", params)
        second = await asyncio.wait_for(anext(iterator), 1.0)
        await second.respond(FileChangeRequestApprovalResponse.from_dict(response_value))
        self.assertEqual([write["id"] for write in peer.writes if "result" in write][-2:], [1, 2])
        await iterator.aclose()
        await session.close()

    async def test_callback_capacity_counts_unresolved_not_queue_occupancy(self) -> None:
        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer, limits=ClientLimits(max_callbacks=1))
        params = model_fixture("FileChangeRequestApprovalParams")
        assert isinstance(params, dict)
        peer.queue_callback(1, "item/fileChange/requestApproval", params)
        callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
        peer.queue_callback(2, "item/fileChange/requestApproval", params)
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        response_value = model_fixture("FileChangeRequestApprovalResponse")
        assert isinstance(response_value, dict)
        with self.assertRaises(CallbackCapacityError):
            await callback.respond(FileChangeRequestApprovalResponse.from_dict(response_value))
        self.assertEqual(peer.close_count, 1)

    async def test_duplicate_pending_callback_id_and_boolean_id_fail_closed(self) -> None:
        for duplicate in (True, False):
            with self.subTest(boolean_id=duplicate):
                peer = ScriptedSessionPeer()
                client, session = await self.initialize(peer)
                params = model_fixture("FileChangeRequestApprovalParams")
                assert isinstance(params, dict)
                if duplicate:
                    peer.queue_callback(7, "item/fileChange/requestApproval", params)
                    await asyncio.wait_for(anext(session.callbacks()), 1.0)
                    peer.queue_callback(7, "item/fileChange/requestApproval", params)
                    expected = CorrelationError
                else:
                    peer.queue_callback(True, "item/fileChange/requestApproval", params)
                    expected = JsonRpcValidationError
                await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                with self.assertRaises(expected):
                    await anext(session.callbacks())

    async def test_out_of_range_callback_id_and_mixed_response_fail_closed(self) -> None:
        for value in (-(2**63) - 1, 2**63, None):
            with self.subTest(request_id=value):
                peer = ScriptedSessionPeer()
                client, session = await self.initialize(peer)
                params = model_fixture("FileChangeRequestApprovalParams")
                assert isinstance(params, dict)
                peer._queue_notification(
                    {
                        "id": value,
                        "method": "item/fileChange/requestApproval",
                        "params": params,
                    }
                )
                await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                with self.assertRaises(JsonRpcValidationError):
                    await anext(session.callbacks())

        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        peer._queue_notification({"id": 91, "result": {}, "params": {}})
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        with self.assertRaises(JsonRpcValidationError):
            await anext(session.events())

    async def test_inbound_callback_id_namespace_is_separate_from_outbound_calls(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.deferred_methods.add("thread/read")
        _, session = await self.initialize(peer)
        operation = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        )
        request = await self.wait_for_deferred(peer)
        params = model_fixture("FileChangeRequestApprovalParams")
        response_value = model_fixture("FileChangeRequestApprovalResponse")
        assert isinstance(params, dict)
        assert isinstance(response_value, dict)
        request_id = request["id"]
        assert isinstance(request_id, int)
        peer.queue_callback(request_id, "item/fileChange/requestApproval", params)
        callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
        await callback.respond(FileChangeRequestApprovalResponse.from_dict(response_value))
        peer.queue_response(request, model_fixture("ThreadReadResponse"))
        result = await operation
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        self.assertEqual(peer.writes[-1]["id"], request_id)
        await session.close()

    async def test_timeout_abandons_late_response_and_session_remains_usable(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.deferred_methods.add("thread/read")
        _, session = await self.initialize(peer)
        with self.assertRaises(CallTimeoutError):
            await session.read_thread(client_api.ThreadReadParams(threadId="thread"), timeout=0.01)
        request = peer.deferred_requests[-1]
        peer.queue_response(request, model_fixture("ThreadReadResponse"))
        peer.deferred_methods.clear()
        await asyncio.sleep(0)
        result = await session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        await session.close()

    async def test_timeout_during_write_retains_late_success_and_error_safely(self) -> None:
        import codex_app_server_client as client_api

        for remote_error in (False, True):
            with self.subTest(remote_error=remote_error):
                peer = ScriptedSessionPeer()
                _, session = await self.initialize(peer)
                peer.request_write_gate = asyncio.Event()
                if remote_error:
                    peer.error_overrides["thread/read"] = {
                        "code": -32_000,
                        "message": "private-late-error",
                    }
                operation = asyncio.create_task(
                    session.read_thread(
                        client_api.ThreadReadParams(threadId="thread"), timeout=0.01
                    )
                )
                await peer.request_write_started.wait()
                with self.assertRaises(CallTimeoutError):
                    await operation
                peer.request_write_gate.set()
                for _ in range(100):
                    if any(write.get("method") == "thread/read" for write in peer.writes):
                        break
                    await asyncio.sleep(0)
                await asyncio.sleep(0)
                peer.error_overrides.clear()
                result = await session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                self.assertIsInstance(result, client_api.ThreadReadResponse)
                self.assertIsNone(session._client._engine.failure)
                await session.close()

    async def test_timeout_during_write_then_write_loss_closes_connection(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        peer.request_write_gate = asyncio.Event()
        operation = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="thread"), timeout=0.01)
        )
        await peer.request_write_started.wait()
        with self.assertRaises(CallTimeoutError):
            await operation
        peer.closed = True
        peer.request_write_gate.set()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        self.assertIsInstance(client._engine.failure, DisconnectedError)
        with self.assertRaises(DisconnectedError):
            await anext(session.events())

    async def test_retained_timed_out_and_cancelled_writes_hold_request_capacity(
        self,
    ) -> None:
        import codex_app_server_client as client_api

        for terminal_cause in ("timeout", "cancellation"):
            with self.subTest(terminal_cause=terminal_cause):
                peer = ScriptedSessionPeer()
                client, session = await self.initialize(
                    peer, limits=ClientLimits(max_pending_calls=1)
                )
                peer.request_write_gate = asyncio.Event()
                if terminal_cause == "timeout":
                    with self.assertRaises(CallTimeoutError):
                        await session.read_thread(
                            client_api.ThreadReadParams(threadId="thread"), timeout=0.01
                        )
                else:
                    operation = asyncio.create_task(
                        session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                    )
                    await peer.request_write_started.wait()
                    operation.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await operation
                self.assertEqual(client._engine.pending_count, 0)
                self.assertEqual(len(client._engine._request_writes), 1)
                for _ in range(2):
                    with self.assertRaises(RequestLimitError):
                        await session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                self.assertEqual(
                    sum(write.get("method") == "thread/read" for write in peer.writes),
                    0,
                )
                peer.request_write_gate.set()
                for _ in range(100):
                    if not client._engine._request_writes and not client._engine._abandoned:
                        break
                    await asyncio.sleep(0)
                self.assertEqual(len(client._engine._request_writes), 0)
                self.assertEqual(len(client._engine._abandoned), 0)
                self.assertIsNone(client._engine.failure)
                result = await session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                self.assertIsInstance(result, client_api.ThreadReadResponse)
                self.assertEqual(
                    sum(write.get("method") == "thread/read" for write in peer.writes),
                    2,
                )
                await session.close()

    async def test_written_abandoned_calls_hold_capacity_until_late_response(self) -> None:
        import codex_app_server_client as client_api

        for terminal_cause in ("timeout", "cancellation"):
            with self.subTest(terminal_cause=terminal_cause):
                peer = ScriptedSessionPeer()
                peer.deferred_methods.add("thread/read")
                client, session = await self.initialize(
                    peer, limits=ClientLimits(max_pending_calls=1)
                )
                operation = asyncio.create_task(
                    session.read_thread(
                        client_api.ThreadReadParams(threadId="thread"),
                        timeout=0.01 if terminal_cause == "timeout" else None,
                    )
                )
                request = await self.wait_for_deferred(peer)
                if terminal_cause == "timeout":
                    with self.assertRaises(CallTimeoutError):
                        await operation
                else:
                    operation.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await operation
                self.assertEqual(client._engine.pending_count, 0)
                self.assertEqual(len(client._engine._request_writes), 0)
                self.assertEqual(len(client._engine._abandoned), 1)
                for _ in range(2):
                    with self.assertRaises(RequestLimitError):
                        await session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                peer.queue_response(request, model_fixture("ThreadReadResponse"))
                for _ in range(100):
                    if not client._engine._abandoned:
                        break
                    await asyncio.sleep(0)
                self.assertEqual(len(client._engine._abandoned), 0)
                self.assertIsNone(client._engine.failure)
                peer.deferred_methods.clear()
                result = await session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                self.assertIsInstance(result, client_api.ThreadReadResponse)
                await session.close()

    async def test_selected_call_response_wins_cancellation_before_waiter_resumes(self) -> None:
        import codex_app_server_client as client_api

        for remote_error in (False, True):
            with self.subTest(remote_error=remote_error):
                peer = ScriptedSessionPeer()
                peer.deferred_methods.add("thread/read")
                client, session = await self.initialize(peer)
                operation = asyncio.create_task(
                    session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                )
                request = await self.wait_for_deferred(peer)
                response = (
                    {
                        "id": request["id"],
                        "error": {"code": -32_000, "message": "private-selected-error"},
                    }
                    if remote_error
                    else {
                        "id": request["id"],
                        "result": model_fixture("ThreadReadResponse"),
                    }
                )
                client._engine._accept_message(json.dumps(response).encode("utf-8") + b"\n")
                self.assertEqual(client._engine.pending_count, 0)
                operation.cancel()
                operation.cancel()
                if remote_error:
                    with self.assertRaises(RemoteRpcError):
                        await operation
                else:
                    result = await operation
                    self.assertIsInstance(result, client_api.ThreadReadResponse)
                self.assertEqual(operation.cancelling(), 0)
                await session.close()

    async def test_selected_call_response_wins_cancellation_during_retained_write(self) -> None:
        import codex_app_server_client as client_api

        for remote_error in (False, True):
            with self.subTest(remote_error=remote_error):
                peer = ScriptedSessionPeer()
                peer.request_write_return_gate = asyncio.Event()
                if remote_error:
                    peer.error_overrides["thread/read"] = {
                        "code": -32_000,
                        "message": "private-selected-error",
                    }
                client, session = await self.initialize(peer)
                operation = asyncio.create_task(
                    session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                )
                await peer.request_response_queued.wait()
                for _ in range(100):
                    if client._engine.pending_count == 0:
                        break
                    await asyncio.sleep(0)
                self.assertEqual(client._engine.pending_count, 0)
                operation.cancel()
                operation.cancel()
                if remote_error:
                    with self.assertRaises(RemoteRpcError):
                        await operation
                else:
                    result = await operation
                    self.assertIsInstance(result, client_api.ThreadReadResponse)
                self.assertEqual(operation.cancelling(), 0)
                peer.request_write_return_gate.set()
                await peer.request_write_returned.wait()
                await asyncio.sleep(0)
                await session.close()

    async def test_selected_call_response_completes_before_retained_write_loss(self) -> None:
        import codex_app_server_client as client_api

        for remote_error in (False, True):
            with self.subTest(remote_error=remote_error):
                peer = ScriptedSessionPeer()
                peer.request_write_return_gate = asyncio.Event()
                if remote_error:
                    peer.error_overrides["thread/read"] = {
                        "code": -32_000,
                        "message": "private-selected-error",
                    }
                client, session = await self.initialize(peer)
                operation = asyncio.create_task(
                    session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                )
                await peer.request_response_queued.wait()
                for _ in range(100):
                    if client._engine.pending_count == 0 and operation.done():
                        break
                    await asyncio.sleep(0)
                self.assertTrue(operation.done())
                if remote_error:
                    with self.assertRaises(RemoteRpcError):
                        await operation
                else:
                    result = await operation
                    self.assertIsInstance(result, client_api.ThreadReadResponse)
                peer.closed = True
                peer.request_write_return_gate.set()
                await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                self.assertIsInstance(client._engine.failure, DisconnectedError)

    async def test_selected_call_response_wins_explicit_close_during_write(self) -> None:
        import codex_app_server_client as client_api

        for remote_error in (False, True):
            with self.subTest(remote_error=remote_error):
                peer = ScriptedSessionPeer()
                peer.request_write_return_gate = asyncio.Event()
                if remote_error:
                    peer.error_overrides["thread/read"] = {
                        "code": -32_000,
                        "message": "private-selected-error",
                    }
                client, session = await self.initialize(peer)
                operation = asyncio.create_task(
                    session.read_thread(client_api.ThreadReadParams(threadId="thread"))
                )
                await peer.request_response_queued.wait()
                for _ in range(100):
                    if client._engine.pending_count == 0:
                        break
                    await asyncio.sleep(0)
                self.assertEqual(client._engine.pending_count, 0)
                await asyncio.wait_for(session.close(), 1.0)
                if remote_error:
                    with self.assertRaises(RemoteRpcError):
                        await operation
                else:
                    result = await operation
                    self.assertIsInstance(result, client_api.ThreadReadResponse)

    async def test_task_cancellation_propagates_and_late_response_is_ignored(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.deferred_methods.add("thread/read")
        _, session = await self.initialize(peer)
        operation = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        )
        request = await self.wait_for_deferred(peer)
        operation.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await operation
        peer.queue_response(request, model_fixture("ThreadReadResponse"))
        peer.deferred_methods.clear()
        await asyncio.sleep(0)
        result = await session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        await session.close()

    async def test_task_cancellation_during_write_retains_one_safe_write(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        peer.request_write_gate = asyncio.Event()
        operation = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        )
        await peer.request_write_started.wait()
        operation.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await operation
        peer.request_write_gate.set()
        for _ in range(100):
            if any(write.get("method") == "thread/read" for write in peer.writes):
                break
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        result = await session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        self.assertEqual(sum(write.get("method") == "thread/read" for write in peer.writes), 2)
        await session.close()

    async def test_disconnect_terminates_call_iterator_and_unanswered_callback(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.deferred_methods.add("thread/read")
        _, session = await self.initialize(peer)
        params = model_fixture("ToolRequestUserInputParams")
        assert isinstance(params, dict)
        peer.queue_callback("question", "item/tool/requestUserInput", params)
        callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
        operation = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        )
        await self.wait_for_deferred(peer)
        event_waiter = asyncio.create_task(anext(session.events()))
        await asyncio.sleep(0)
        peer.disconnect()
        with self.assertRaises(DisconnectedError):
            await operation
        with self.assertRaises(DisconnectedError):
            await event_waiter
        response_value = model_fixture("ToolRequestUserInputResponse")
        assert isinstance(response_value, dict)
        with self.assertRaises(DisconnectedError) as raised:
            await callback.respond(ToolRequestUserInputResponse.from_dict(response_value))
        self.assertNotIn("private-disconnect-content", repr(raised.exception))
        self.assertEqual(peer.close_count, 1)

    async def test_explicit_close_ends_streams_and_cancels_unanswered_callback(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        params = model_fixture("ToolRequestUserInputParams")
        assert isinstance(params, dict)
        peer.queue_callback("question", "item/tool/requestUserInput", params)
        callback_iterator = session.callbacks()
        callback = await asyncio.wait_for(anext(callback_iterator), 1.0)
        event_waiter = asyncio.create_task(anext(session.events()))
        callback_waiter = asyncio.create_task(anext(callback_iterator))
        await asyncio.sleep(0)
        await session.close()
        with self.assertRaises(StopAsyncIteration):
            await event_waiter
        with self.assertRaises(StopAsyncIteration):
            await callback_waiter
        response_value = model_fixture("ToolRequestUserInputResponse")
        assert isinstance(response_value, dict)
        with self.assertRaises(CallCancelledError):
            await callback.respond(ToolRequestUserInputResponse.from_dict(response_value))

    async def test_explicit_close_terminates_pending_call_with_typed_cancellation(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.deferred_methods.add("thread/read")
        _, session = await self.initialize(peer)
        operation = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="thread"))
        )
        await self.wait_for_deferred(peer)
        await asyncio.sleep(0)
        await session.close()
        with self.assertRaises(CallCancelledError):
            await operation

    async def test_callback_response_write_loss_is_terminal_and_content_free(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        params = model_fixture("FileChangeRequestApprovalParams")
        response_value = model_fixture("FileChangeRequestApprovalResponse")
        assert isinstance(params, dict)
        assert isinstance(response_value, dict)
        peer.queue_callback("approval", "item/fileChange/requestApproval", params)
        callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
        peer.closed = True
        response = FileChangeRequestApprovalResponse.from_dict(response_value)
        with self.assertRaises(DisconnectedError) as raised:
            await callback.respond(response)
        self.assertNotIn("private", repr(vars(raised.exception)))
        with self.assertRaises(DisconnectedError):
            await callback.respond(response)
        self.assertEqual(
            sum(write.get("id") == "approval" and "result" in write for write in peer.writes),
            1,
        )

    async def test_callback_response_preflight_failure_allows_one_corrected_retry(self) -> None:
        for invalid_answer, expected_error in (
            ("x" * 70_000, MessageTooLargeError),
            ("\ud800", JsonRpcValidationError),
        ):
            with self.subTest(expected_error=expected_error.__name__):
                peer = ScriptedSessionPeer()
                client, session = await self.initialize(
                    peer, limits=ClientLimits(max_message_bytes=65_536)
                )
                params = model_fixture("ToolRequestUserInputParams")
                assert isinstance(params, dict)
                peer.queue_callback("question", "item/tool/requestUserInput", params)
                callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
                invalid = ToolRequestUserInputResponse.from_dict(
                    {"answers": {"question": {"answers": [invalid_answer]}}}
                )
                before = len(peer.writes)
                with self.assertRaises(expected_error):
                    await callback.respond(invalid)
                self.assertIsNone(client._engine.failure)
                self.assertEqual(callback._state.status, "pending")
                self.assertEqual(len(client._coordinator._callback_states), 1)
                self.assertEqual(len(peer.writes), before)
                corrected = ToolRequestUserInputResponse.from_dict(
                    {"answers": {"question": {"answers": ["corrected"]}}}
                )
                await callback.respond(corrected)
                self.assertEqual(callback._state.status, "resolved")
                self.assertEqual(len(client._coordinator._callback_states), 0)
                self.assertEqual(len(peer.writes), before + 1)
                await session.close()

    async def test_only_one_event_iterator_can_be_active(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        first = session.events()
        first_waiter = asyncio.create_task(anext(first))
        await asyncio.sleep(0)
        second = session.events()
        with self.assertRaises(SessionStateError):
            await anext(second)
        first_waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first_waiter
        await session.close()

    async def test_event_iterator_aclose_after_yield_releases_claim(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        peer._queue_notification({"method": "warning", "params": {"message": "first"}})
        first = session.events()
        self.assertEqual((await anext(first)).message, "first")
        await first.aclose()
        peer._queue_notification({"method": "warning", "params": {"message": "second"}})
        successor = session.events()
        self.assertEqual((await asyncio.wait_for(anext(successor), 1.0)).message, "second")
        await successor.aclose()
        await session.close()

    async def test_event_iterator_cancellation_after_yield_releases_claim(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        peer._queue_notification({"method": "warning", "params": {"message": "first"}})
        first = session.events()
        await anext(first)
        waiter = asyncio.create_task(anext(first))
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        peer._queue_notification({"method": "warning", "params": {"message": "second"}})
        successor = session.events()
        self.assertEqual((await asyncio.wait_for(anext(successor), 1.0)).message, "second")
        await successor.aclose()
        await session.close()

    async def test_callback_iterator_aclose_after_yield_releases_claim(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        params = model_fixture("FileChangeRequestApprovalParams")
        response_value = model_fixture("FileChangeRequestApprovalResponse")
        assert isinstance(params, dict)
        assert isinstance(response_value, dict)
        peer.queue_callback(1, "item/fileChange/requestApproval", params)
        first = session.callbacks()
        first_callback = await asyncio.wait_for(anext(first), 1.0)
        await first.aclose()
        peer.queue_callback(2, "item/fileChange/requestApproval", params)
        successor = session.callbacks()
        second_callback = await asyncio.wait_for(anext(successor), 1.0)
        response = FileChangeRequestApprovalResponse.from_dict(response_value)
        await first_callback.respond(response)
        await second_callback.respond(response)
        await successor.aclose()
        await session.close()

    async def test_callback_iterator_cancellation_after_yield_releases_claim(self) -> None:
        peer = ScriptedSessionPeer()
        _, session = await self.initialize(peer)
        params = model_fixture("FileChangeRequestApprovalParams")
        response_value = model_fixture("FileChangeRequestApprovalResponse")
        assert isinstance(params, dict)
        assert isinstance(response_value, dict)
        peer.queue_callback(1, "item/fileChange/requestApproval", params)
        first = session.callbacks()
        first_callback = await asyncio.wait_for(anext(first), 1.0)
        waiter = asyncio.create_task(anext(first))
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        peer.queue_callback(2, "item/fileChange/requestApproval", params)
        successor = session.callbacks()
        second_callback = await asyncio.wait_for(anext(successor), 1.0)
        response = FileChangeRequestApprovalResponse.from_dict(response_value)
        await first_callback.respond(response)
        await second_callback.respond(response)
        await successor.aclose()
        await session.close()

    async def test_cancelled_callback_waiter_does_not_cancel_selected_response(self) -> None:
        for cancellation_count in (1, 2):
            with self.subTest(cancellation_count=cancellation_count):
                peer = ScriptedSessionPeer()
                peer.callback_response_gate = asyncio.Event()
                client, session = await self.initialize(peer, limits=ClientLimits(max_callbacks=1))
                params = model_fixture("CommandExecutionRequestApprovalParams")
                assert isinstance(params, dict)
                request_id = f"approval-{cancellation_count}"
                peer.queue_callback(request_id, "item/commandExecution/requestApproval", params)
                callbacks = session.callbacks()
                callback = await asyncio.wait_for(anext(callbacks), 1.0)
                response_value = model_fixture("CommandExecutionRequestApprovalResponse")
                assert isinstance(response_value, dict)
                response = CommandExecutionRequestApprovalResponse.from_dict(response_value)
                waiter = asyncio.create_task(callback.respond(response))
                await peer.callback_response_started.wait()
                for _ in range(cancellation_count):
                    waiter.cancel()
                with self.assertRaises(CallCancelledError):
                    await waiter
                self.assertFalse(waiter.cancelled())
                self.assertEqual(waiter.cancelling(), 0)
                peer.callback_response_gate.set()
                for _ in range(100):
                    if callback._state.status == "resolved":
                        break
                    await asyncio.sleep(0)
                self.assertEqual(callback._state.status, "resolved")
                self.assertEqual(len(client._coordinator._callback_states), 0)
                with self.assertRaises(CallCancelledError):
                    await callback.respond(response)
                self.assertEqual(
                    sum(
                        write.get("id") == request_id and "result" in write for write in peer.writes
                    ),
                    1,
                )
                successor_id = f"successor-{cancellation_count}"
                peer.queue_callback(successor_id, "item/commandExecution/requestApproval", params)
                successor = await asyncio.wait_for(anext(callbacks), 1.0)
                await successor.respond(response)
                self.assertEqual(
                    sum(
                        write.get("id") == successor_id and "result" in write
                        for write in peer.writes
                    ),
                    1,
                )
                self.assertEqual(len(client._coordinator._callback_states), 0)
                await callbacks.aclose()
                await session.close()

    def test_restart_contract_is_frozen_and_content_free(self) -> None:
        import codex_app_server_client as client_api

        cause = DisconnectedError("connection generation failed")
        context = RestartContext(1, 2, cause)
        self.assertEqual(context.failed_generation, 1)
        self.assertEqual(context.replacement_generation, 2)
        self.assertIs(context.cause, cause)
        with self.assertRaises(FrozenInstanceError):
            context.failed_generation = 2  # type: ignore[misc]
        for values, expected_error in (
            ((True, 2, cause), ValueError),
            ((0, 1, cause), ValueError),
            ((1, True, cause), ValueError),
            ((1, 2.0, cause), ValueError),
            ((1, 2 + 0j, cause), ValueError),
            ((1, 3, cause), ValueError),
            ((1, 2, RuntimeError("private")), TypeError),
        ):
            with self.subTest(values=values[:2]), self.assertRaises(expected_error):
                RestartContext(*values)  # type: ignore[arg-type]
        self.assertEqual(
            str(inspect.signature(AppServerClient.replace)),
            "(self, transport: 'ClientTransport', *, backoff: 'BackoffHook | None' = None) "
            "-> 'AppServerSession'",
        )
        self.assertIsNotNone(client_api.BackoffHook)
        self.assertIs(client_api.RestartContext, RestartContext)
        self.assertIs(client_api.RestartError, RestartError)
        self.assertIs(client_api.StaleGenerationError, StaleGenerationError)
        self.assertEqual(len(client_api.__all__), 92)

    async def test_backoff_hook_is_bounded_before_replacement_transport_claim(self) -> None:
        class HostileInt(int):
            def __float__(self) -> float:
                raise RuntimeError("private-hook-content")

        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        replacement_peer = ScriptedSessionPeer()
        transport = InjectedTransport(replacement_peer, ownership=TransportOwnership.OWNED)
        contexts: list[RestartContext] = []

        def invalid_hook(context: RestartContext, value: object) -> object:
            contexts.append(context)
            return value

        for value in (
            True,
            -1,
            float("inf"),
            float("nan"),
            31.0,
            10**10000,
            HostileInt(1),
            "private",
        ):
            with self.subTest(value=value):
                with self.assertRaises(RestartError) as raised:
                    await client.replace(
                        transport,
                        backoff=lambda context, value=value: invalid_hook(context, value),
                    )
                self.assertEqual(raised.exception.phase, "backoff-bound")
                self.assertEqual(replacement_peer.writes, [])
                self.assertEqual(replacement_peer.close_count, 0)

        def failed_hook(context: RestartContext) -> float:
            contexts.append(context)
            raise RuntimeError("private-backoff-content")

        with self.assertRaises(RestartError) as raised:
            await client.replace(transport, backoff=failed_hook)
        self.assertEqual(raised.exception.phase, "backoff-hook")
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        self.assertNotIn("private", repr(vars(raised.exception)))
        self.assertTrue(contexts)
        self.assertTrue(all(context.failed_generation == 1 for context in contexts))
        self.assertTrue(all(context.replacement_generation == 2 for context in contexts))
        self.assertTrue(all(isinstance(context.cause, DisconnectedError) for context in contexts))

        async def async_hook(_context: RestartContext) -> float:
            return 0.0

        with self.assertRaises(RestartError) as raised:
            await client.replace(transport, backoff=async_hook)  # type: ignore[arg-type]
        self.assertEqual(raised.exception.phase, "backoff-bound")
        self.assertEqual(replacement_peer.writes, [])
        replacement = await client.replace(transport, backoff=lambda context: 0.0)
        self.assertEqual(replacement.generation, 2)
        with self.assertRaises(StaleGenerationError):
            await session.close()
        await replacement.close()

    def test_client_limits_reject_huge_backoff_bound_without_overflow(self) -> None:
        class HostileInt(int):
            def __float__(self) -> float:
                raise RuntimeError("private-limit-content")

        for value in (10**10000, HostileInt(1)):
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError) as raised:
                ClientLimits(max_backoff_seconds=value)
            self.assertEqual(
                str(raised.exception), "max_backoff_seconds must be positive and finite"
            )

    async def test_replace_discards_old_event_callback_and_close_effects(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        peer._queue_notification(
            {"method": "warning", "params": {"message": "old-generation-event"}}
        )
        callback_params = model_fixture("CommandExecutionRequestApprovalParams")
        assert isinstance(callback_params, dict)
        peer.queue_callback(
            "old-callback", "item/commandExecution/requestApproval", callback_params
        )
        for _ in range(100):
            if client._coordinator._events and client._coordinator._callbacks:
                break
            await asyncio.sleep(0)
        self.assertEqual(len(client._coordinator._events), 1)
        old_callback = client._coordinator._callbacks[0]
        self.assertEqual(old_callback._state.generation, 1)
        client._engine._begin_failure(DisconnectedError("connection generation failed"))
        replacement_peer = ScriptedSessionPeer()
        replacement = await client.replace(
            InjectedTransport(replacement_peer, ownership=TransportOwnership.OWNED)
        )
        self.assertEqual(replacement.generation, 2)
        self.assertEqual(client._engine._generation, 2)
        self.assertEqual(client._coordinator._generation, 2)
        self.assertEqual(len(session._coordinator._events), 0)
        self.assertEqual(len(session._coordinator._callbacks), 0)
        with self.assertRaises(StaleGenerationError) as event_error:
            await anext(session.events())
        self.assertEqual(event_error.exception.generation, 1)
        with self.assertRaises(StaleGenerationError):
            await anext(session.callbacks())
        response_value = model_fixture("CommandExecutionRequestApprovalResponse")
        assert isinstance(response_value, dict)
        with self.assertRaises(StaleGenerationError):
            await old_callback.respond(
                CommandExecutionRequestApprovalResponse.from_dict(response_value)
            )
        with self.assertRaises(StaleGenerationError):
            await session.close()
        result = await replacement.read_thread(client_api.ThreadReadParams(threadId="replacement"))
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        self.assertFalse(replacement_peer.closed)
        await replacement.close()

    async def test_replace_rejects_reused_injected_channel_lineage(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        original_transport = InjectedTransport(peer, ownership=TransportOwnership.BORROWED)
        client = await AppServerClient.connect(
            original_transport, self.compatibility, limits=ClientLimits()
        )
        session = await client.initialize(ClientIdentity("fixture", "1.0"))
        peer.deferred_methods.add("thread/read")
        old_call = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="old"))
        )
        old_request = await self.wait_for_deferred(peer)
        peer.disconnect()
        with self.assertRaises(DisconnectedError):
            await old_call
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)

        stale_result = model_fixture("ThreadReadResponse")
        callback_params = model_fixture("CommandExecutionRequestApprovalParams")
        assert isinstance(stale_result, dict)
        assert isinstance(callback_params, dict)
        thread = stale_result["thread"]
        assert isinstance(thread, dict)
        thread["id"] = "stale-old-generation"
        peer.queue_response(old_request, stale_result)
        peer._queue_notification(
            {"method": "warning", "params": {"message": "stale-old-generation"}}
        )
        peer.queue_callback(
            "stale-callback",
            "item/commandExecution/requestApproval",
            callback_params,
        )
        writes_before_reuse = list(peer.writes)
        reused = InjectedTransport(peer, ownership=TransportOwnership.BORROWED)
        with self.assertRaises(RestartError) as raised:
            await client.replace(reused)
        self.assertEqual(raised.exception.phase, "transport-lineage")
        self.assertFalse(reused._claimed)
        self.assertEqual(peer.writes, writes_before_reuse)
        self.assertEqual(peer.incoming.qsize(), 3)
        self.assertEqual(peer.close_count, 0)

        fresh_peer = ScriptedSessionPeer()
        replacement = await client.replace(
            InjectedTransport(fresh_peer, ownership=TransportOwnership.BORROWED)
        )
        result = await replacement.read_thread(client_api.ThreadReadParams(threadId="current"))
        self.assertNotEqual(result.thread.id, "stale-old-generation")
        self.assertEqual(peer.incoming.qsize(), 3)
        await replacement.close()
        self.assertEqual(fresh_peer.close_count, 0)

    async def test_structural_transport_cannot_rewrap_one_channel_lineage(self) -> None:
        import codex_app_server_client as client_api

        class ReusablePeer(ScriptedSessionPeer):
            async def close(self) -> None:
                self.close_count += 1

        class StructuralTransport:
            capability = TransportCapability.INJECTED_BYTE_CHANNEL

            def __init__(self, channel: ReusablePeer) -> None:
                self.channel = channel
                self.claimed = False

            async def _open_channel(self) -> ReusablePeer:
                if self.claimed:
                    raise RuntimeError("structural transport already claimed")
                self.claimed = True
                return self.channel

        class DeclaredStructuralTransport(StructuralTransport):
            def _connection_lineage(self) -> object:
                return self.channel

        peer = ReusablePeer()
        client = await AppServerClient.connect(
            StructuralTransport(peer),  # type: ignore[arg-type]
            self.compatibility,
            limits=ClientLimits(),
        )
        session = await client.initialize(ClientIdentity("fixture", "1.0"))
        peer.deferred_methods.add("thread/read")
        old_call = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="old"))
        )
        old_request = await self.wait_for_deferred(peer)
        peer.disconnect()
        with self.assertRaises(DisconnectedError):
            await old_call
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)

        stale_result = model_fixture("ThreadReadResponse")
        callback_params = model_fixture("CommandExecutionRequestApprovalParams")
        assert isinstance(stale_result, dict)
        assert isinstance(callback_params, dict)
        thread = stale_result["thread"]
        assert isinstance(thread, dict)
        thread["id"] = "stale-structural-lineage"
        peer.queue_response(old_request, stale_result)
        peer._queue_notification(
            {"method": "warning", "params": {"message": "stale-structural-lineage"}}
        )
        peer.queue_callback(
            "stale-structural-callback",
            "item/commandExecution/requestApproval",
            callback_params,
        )
        writes_before_reuse = list(peer.writes)
        reused = StructuralTransport(peer)
        with self.assertRaises(RestartError) as raised:
            await client.replace(reused)  # type: ignore[arg-type]
        self.assertEqual(raised.exception.phase, "transport-lineage")
        self.assertFalse(reused.claimed)
        declared_reuse = DeclaredStructuralTransport(peer)
        with self.assertRaises(RestartError) as declared_error:
            await client.replace(declared_reuse)  # type: ignore[arg-type]
        self.assertEqual(declared_error.exception.phase, "transport-lineage")
        self.assertFalse(declared_reuse.claimed)
        self.assertEqual(peer.writes, writes_before_reuse)
        self.assertEqual(peer.incoming.qsize(), 3)

        fresh_peer = ScriptedSessionPeer()
        replacement = await client.replace(
            InjectedTransport(fresh_peer, ownership=TransportOwnership.OWNED)
        )
        self.assertEqual(replacement.generation, 2)
        result = await replacement.read_thread(client_api.ThreadReadParams(threadId="current"))
        self.assertNotEqual(result.thread.id, "stale-structural-lineage")
        self.assertEqual(peer.incoming.qsize(), 3)
        await replacement.close()

    async def test_lineage_history_is_weak_bounded_and_nonweak_fails_closed(
        self,
    ) -> None:
        first_peer = ScriptedSessionPeer()
        client, first_session = await self.initialize(
            first_peer, limits=ClientLimits(max_connection_lineages=2)
        )
        first_reference = weakref.ref(first_peer)
        self.assertTrue(
            all(
                isinstance(reference, weakref.ReferenceType)
                for reference in client._connection_lineages
            )
        )
        first_peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        second_peer = ScriptedSessionPeer()
        second_session = await client.replace(
            InjectedTransport(second_peer, ownership=TransportOwnership.BORROWED)
        )
        second_peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        capacity_peer = ScriptedSessionPeer()
        capacity_transport = InjectedTransport(capacity_peer, ownership=TransportOwnership.BORROWED)
        with self.assertRaises(RestartError) as capacity_error:
            await client.replace(capacity_transport)
        self.assertEqual(capacity_error.exception.phase, "transport-lineage")
        self.assertFalse(capacity_transport._claimed)

        del first_session
        del first_peer
        for _ in range(3):
            await asyncio.sleep(0)
            gc.collect()
        self.assertIsNone(first_reference())
        replacement_peer = ScriptedSessionPeer()
        replacement = await client.replace(
            InjectedTransport(replacement_peer, ownership=TransportOwnership.BORROWED)
        )
        self.assertEqual(replacement.generation, 3)
        self.assertLessEqual(len(client._connection_lineages), 2)
        await replacement.close()
        del second_session

        class NonWeakChannel:
            __slots__ = ("peer",)

            def __init__(self, peer: ScriptedSessionPeer) -> None:
                self.peer = peer

            async def read_line(self, *, max_bytes: int) -> bytes:
                return await self.peer.read_line(max_bytes=max_bytes)

            async def write_line(self, data: bytes) -> None:
                await self.peer.write_line(data)

            async def close(self) -> None:
                await self.peer.close()

        nonweak_peer = ScriptedSessionPeer()
        nonweak_channel = NonWeakChannel(nonweak_peer)
        nonweak_client = await AppServerClient.connect(
            InjectedTransport(
                nonweak_channel,  # type: ignore[arg-type]
                ownership=TransportOwnership.BORROWED,
            ),
            self.compatibility,
        )
        await nonweak_client.initialize(ClientIdentity("fixture", "1.0"))
        nonweak_peer.disconnect()
        await asyncio.wait_for(nonweak_client._engine.wait_closed(), 1.0)
        nonweak_replacement = InjectedTransport(
            nonweak_channel,  # type: ignore[arg-type]
            ownership=TransportOwnership.BORROWED,
        )
        with self.assertRaises(RestartError) as nonweak_error:
            await nonweak_client.replace(nonweak_replacement)
        self.assertEqual(nonweak_error.exception.phase, "transport-lineage")
        self.assertFalse(nonweak_replacement._claimed)

    async def test_selected_old_response_cannot_publish_after_replacement(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.deferred_methods.add("thread/read")
        client, session = await self.initialize(peer)
        operation = asyncio.create_task(
            session.read_thread(client_api.ThreadReadParams(threadId="old"))
        )
        request = await self.wait_for_deferred(peer)
        client._engine._accept_message(
            json.dumps({"id": request["id"], "result": model_fixture("ThreadReadResponse")}).encode(
                "utf-8"
            )
            + b"\n"
        )
        client._engine._begin_failure(DisconnectedError("connection generation failed"))
        replacement_peer = ScriptedSessionPeer()
        replacement = await client.replace(
            InjectedTransport(replacement_peer, ownership=TransportOwnership.OWNED)
        )
        with self.assertRaises(StaleGenerationError):
            await operation
        result = await replacement.read_thread(client_api.ThreadReadParams(threadId="replacement"))
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        self.assertEqual(
            sum(write.get("method") == "thread/read" for write in replacement_peer.writes),
            1,
        )
        await replacement.close()

    async def test_old_prewrite_cancellation_and_timeout_cannot_touch_replacement(
        self,
    ) -> None:
        import codex_app_server_client as client_api

        for terminal in ("cancellation", "timeout"):
            with self.subTest(terminal=terminal):
                peer = ScriptedSessionPeer()
                client, session = await self.initialize(peer)
                peer.request_write_gate = asyncio.Event()
                operation = asyncio.create_task(
                    session.read_thread(
                        client_api.ThreadReadParams(threadId="old"),
                        timeout=0.01 if terminal == "timeout" else None,
                    )
                )
                await peer.request_write_started.wait()
                if terminal == "cancellation":
                    operation.cancel()
                else:
                    with self.assertRaises(CallTimeoutError):
                        await operation
                client._engine._begin_failure(DisconnectedError("connection generation failed"))
                replacement_peer = ScriptedSessionPeer()
                replacement = await client.replace(
                    InjectedTransport(replacement_peer, ownership=TransportOwnership.OWNED)
                )
                if terminal == "cancellation":
                    with self.assertRaises(StaleGenerationError):
                        await operation
                self.assertEqual(
                    sum(write.get("method") == "thread/read" for write in peer.writes),
                    0,
                )
                result = await replacement.read_thread(
                    client_api.ThreadReadParams(threadId="replacement"), timeout=1.0
                )
                self.assertIsInstance(result, client_api.ThreadReadResponse)
                self.assertIsNone(client._engine.failure)
                await replacement.close()

    async def test_inflight_old_callback_write_terminates_stale_before_new_owner(
        self,
    ) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        peer.callback_response_gate = asyncio.Event()
        client, session = await self.initialize(peer)
        params = model_fixture("CommandExecutionRequestApprovalParams")
        response_value = model_fixture("CommandExecutionRequestApprovalResponse")
        assert isinstance(params, dict)
        assert isinstance(response_value, dict)
        peer.queue_callback("old-callback", "item/commandExecution/requestApproval", params)
        callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
        response = CommandExecutionRequestApprovalResponse.from_dict(response_value)
        response_waiter = asyncio.create_task(callback.respond(response))
        await peer.callback_response_started.wait()
        client._engine._begin_failure(DisconnectedError("connection generation failed"))
        replacement_peer = ScriptedSessionPeer()
        replacement = await client.replace(
            InjectedTransport(replacement_peer, ownership=TransportOwnership.OWNED)
        )
        with self.assertRaises(StaleGenerationError):
            await response_waiter
        self.assertEqual(
            sum(write.get("id") == "old-callback" and "result" in write for write in peer.writes),
            1,
        )
        self.assertEqual(
            sum(
                write.get("id") == "old-callback" and "result" in write
                for write in replacement_peer.writes
            ),
            0,
        )
        result = await replacement.read_thread(client_api.ThreadReadParams(threadId="replacement"))
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        await replacement.close()

    async def test_callback_completion_is_generation_gated_before_publication(
        self,
    ) -> None:
        for outcome in ("success", "failure", "cancelled-success"):
            with self.subTest(outcome=outcome):
                peer = ScriptedSessionPeer()
                peer.callback_response_gate = asyncio.Event()
                client, session = await self.initialize(peer)
                params = model_fixture("CommandExecutionRequestApprovalParams")
                response_value = model_fixture("CommandExecutionRequestApprovalResponse")
                assert isinstance(params, dict)
                assert isinstance(response_value, dict)
                peer.queue_callback("old-callback", "item/commandExecution/requestApproval", params)
                callback = await asyncio.wait_for(anext(session.callbacks()), 1.0)
                response = CommandExecutionRequestApprovalResponse.from_dict(response_value)
                waiter = asyncio.create_task(callback.respond(response))
                await peer.callback_response_started.wait()
                response_task = callback._state.response_task
                assert response_task is not None
                stale = StaleGenerationError(generation=1, current_generation=2)

                def retire_before_publication(
                    _task: asyncio.Task[None],
                    session: AppServerSession = session,
                    client: AppServerClient = client,
                    stale: StaleGenerationError = stale,
                ) -> None:
                    session._retire(stale)
                    client._coordinator.retire(stale)
                    client._generation = 2

                response_task.add_done_callback(retire_before_publication)
                if outcome == "cancelled-success":

                    def cancel_waiter(
                        _task: asyncio.Task[None],
                        waiter: asyncio.Task[None] = waiter,
                    ) -> None:
                        waiter.cancel()
                        waiter.cancel()

                    response_task.add_done_callback(cancel_waiter)
                if outcome == "failure":
                    peer.closed = True
                peer.callback_response_gate.set()
                with self.assertRaises(StaleGenerationError):
                    await waiter
                self.assertEqual(waiter.cancelling(), 0)
                self.assertIs(client._coordinator._retired_failure, stale)
                await client.close()

    async def test_concurrent_replace_claims_exactly_one_new_transport(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        client, _ = await self.initialize(peer)
        peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        first_peer = ScriptedSessionPeer()
        first_peer.initialize_gate = asyncio.Event()
        first = asyncio.create_task(
            client.replace(InjectedTransport(first_peer, ownership=TransportOwnership.OWNED))
        )
        await first_peer.initialize_started.wait()
        second_peer = ScriptedSessionPeer()
        second_transport = InjectedTransport(second_peer, ownership=TransportOwnership.OWNED)
        second = asyncio.create_task(client.replace(second_transport))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        self.assertEqual(second_peer.writes, [])
        first_peer.initialize_gate.set()
        replacement = await first
        with self.assertRaises(RestartError) as raised:
            await second
        self.assertEqual(raised.exception.phase, "precondition")
        self.assertEqual(second_peer.writes, [])
        result = await replacement.read_thread(client_api.ThreadReadParams(threadId="replacement"))
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        await replacement.close()

    async def test_old_close_racing_replace_cannot_close_new_generation(self) -> None:
        import codex_app_server_client as client_api

        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        replacement_peer = ScriptedSessionPeer()
        replacement_peer.initialize_gate = asyncio.Event()
        replacement_task = asyncio.create_task(
            client.replace(InjectedTransport(replacement_peer, ownership=TransportOwnership.OWNED))
        )
        await replacement_peer.initialize_started.wait()
        stale_close = asyncio.create_task(session.close())
        await asyncio.sleep(0)
        self.assertFalse(stale_close.done())
        replacement_peer.initialize_gate.set()
        replacement = await replacement_task
        with self.assertRaises(StaleGenerationError):
            await stale_close
        self.assertFalse(replacement_peer.closed)
        result = await replacement.read_thread(client_api.ThreadReadParams(threadId="replacement"))
        self.assertIsInstance(result, client_api.ThreadReadResponse)
        await replacement.close()

    async def test_cancelled_and_failed_replacements_advance_attempt_generation_once(
        self,
    ) -> None:
        peer = ScriptedSessionPeer()
        client, session = await self.initialize(peer)
        peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        cancelled_peer = ScriptedSessionPeer()
        cancelled_peer.initialize_gate = asyncio.Event()
        cancelled = asyncio.create_task(
            client.replace(InjectedTransport(cancelled_peer, ownership=TransportOwnership.OWNED))
        )
        await cancelled_peer.initialize_started.wait()
        cancelled.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await cancelled
        self.assertEqual(client._generation, 2)
        self.assertEqual(cancelled_peer.close_count, 1)
        self.assertEqual(client._state, "failed")
        with self.assertRaises(StaleGenerationError):
            await session.close()
        failed_peer = ScriptedSessionPeer()
        failed_peer.initialize_result = {"private": "replacement-content"}
        with self.assertRaises(RestartError) as raised:
            await client.replace(InjectedTransport(failed_peer, ownership=TransportOwnership.OWNED))
        self.assertEqual(raised.exception.failed_generation, 2)
        self.assertEqual(raised.exception.replacement_generation, 3)
        self.assertEqual(raised.exception.phase, "initialization")
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        self.assertNotIn("private", repr(vars(raised.exception)))
        self.assertEqual(failed_peer.close_count, 1)
        final_peer = ScriptedSessionPeer()
        final = await client.replace(
            InjectedTransport(final_peer, ownership=TransportOwnership.OWNED)
        )
        self.assertEqual(final.generation, 4)
        await final.close()

    async def test_repeated_cancellation_rejoins_replacement_cleanup_before_retry(
        self,
    ) -> None:
        peer = ScriptedSessionPeer()
        client, _ = await self.initialize(peer)
        peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        cancelled_peer = ScriptedSessionPeer()
        cancelled_peer.initialize_gate = asyncio.Event()
        cancelled_peer.close_gate = asyncio.Event()
        replacement = asyncio.create_task(
            client.replace(InjectedTransport(cancelled_peer, ownership=TransportOwnership.OWNED))
        )
        await cancelled_peer.initialize_started.wait()
        replacement.cancel()
        await cancelled_peer.close_started.wait()
        replacement.cancel()
        await asyncio.sleep(0)
        self.assertFalse(replacement.done())
        self.assertEqual(client._state, "failed")
        self.assertEqual(client._generation, 2)
        cancelled_peer.close_gate.set()
        with self.assertRaises(asyncio.CancelledError):
            await replacement
        self.assertEqual(cancelled_peer.close_count, 1)
        successor_peer = ScriptedSessionPeer()
        successor = await client.replace(
            InjectedTransport(successor_peer, ownership=TransportOwnership.OWNED)
        )
        self.assertEqual(successor.generation, 3)
        await successor.close()

    async def test_cancelled_replacement_cleanup_failure_leaves_failed_state(
        self,
    ) -> None:
        for cancellation_count in (1, 2):
            with self.subTest(cancellation_count=cancellation_count):
                peer = ScriptedSessionPeer()
                client, _ = await self.initialize(peer)
                peer.disconnect()
                await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                failed_peer = ScriptedSessionPeer()
                failed_peer.initialize_gate = asyncio.Event()
                failed_peer.close_error = RuntimeError("private-cleanup-content")
                replacement = asyncio.create_task(
                    client.replace(
                        InjectedTransport(failed_peer, ownership=TransportOwnership.OWNED)
                    )
                )
                await failed_peer.initialize_started.wait()
                for _ in range(cancellation_count):
                    replacement.cancel()
                with self.assertRaises(RestartError) as raised:
                    await replacement
                self.assertEqual(replacement.cancelling(), 0)
                self.assertEqual(raised.exception.phase, "replacement-cleanup")
                self.assertIsNone(raised.exception.__cause__)
                self.assertIsNone(raised.exception.__context__)
                self.assertNotIn("private", repr(vars(raised.exception)))
                self.assertEqual(client._state, "failed")
                self.assertEqual(client._generation, 2)
                self.assertEqual(failed_peer.close_count, 1)
                successor_peer = ScriptedSessionPeer()
                successor_transport = InjectedTransport(
                    successor_peer, ownership=TransportOwnership.OWNED
                )
                with self.assertRaises(RestartError) as successor_error:
                    await client.replace(successor_transport)
                self.assertEqual(successor_error.exception.phase, "old-generation-cleanup")
                self.assertEqual(successor_peer.writes, [])

    async def test_initialization_failure_cleanup_rejoins_cancellation_before_retry(
        self,
    ) -> None:
        for cancellation_count in (1, 2):
            with self.subTest(cancellation_count=cancellation_count):
                peer = ScriptedSessionPeer()
                client, _ = await self.initialize(peer)
                peer.disconnect()
                await asyncio.wait_for(client._engine.wait_closed(), 1.0)
                failed_peer = ScriptedSessionPeer()
                failed_peer.initialize_result = {"private": "invalid-initialize"}
                failed_peer.close_gate = asyncio.Event()
                replacement = asyncio.create_task(
                    client.replace(
                        InjectedTransport(failed_peer, ownership=TransportOwnership.OWNED)
                    )
                )
                await failed_peer.close_started.wait()
                self.assertEqual(client._state, "failed")
                for _ in range(cancellation_count):
                    replacement.cancel()
                await asyncio.sleep(0)
                self.assertFalse(replacement.done())
                failed_peer.close_gate.set()
                with self.assertRaises(RestartError) as raised:
                    await replacement
                self.assertEqual(replacement.cancelling(), 0)
                self.assertEqual(raised.exception.phase, "initialization")
                self.assertEqual(failed_peer.close_count, 1)
                successor_peer = ScriptedSessionPeer()
                successor = await client.replace(
                    InjectedTransport(successor_peer, ownership=TransportOwnership.OWNED)
                )
                self.assertEqual(successor.generation, 3)
                await successor.close()
