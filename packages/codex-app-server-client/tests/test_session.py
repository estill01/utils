from __future__ import annotations

import asyncio
import inspect
import json
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

from codex_app_server_client import (
    AppServerClient,
    AppServerSession,
    BinaryIdentity,
    ClientIdentity,
    FeatureSet,
    InitializationError,
    InjectedTransport,
    JsonRpcValidationError,
    NotificationCapability,
    RequestCapability,
    SchemaRootMismatchError,
    SessionStateError,
    TransportCapability,
    TransportCleanupError,
    TransportOwnership,
    UnsupportedFeatureError,
    inspect_compatibility,
)
from codex_app_server_client.compatibility import _packaged_protocol_root
from codex_app_server_client.models import (
    _PUBLIC_MODEL_NAMES,
    FrozenJsonObject,
    _collect_model_specs,
    _ModelValidationError,
)


def fake_identity() -> BinaryIdentity:
    return BinaryIdentity(
        path=Path("/nonexistent/codex"), reported_version="0.147.0", sha256="0" * 64
    )


def schema_document(name: str) -> dict[str, object]:
    path = _packaged_protocol_root().joinpath("upstream", "0.147.0", "v2", f"{name}.json")
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
        self.incoming: asyncio.Queue[bytes] = asyncio.Queue()
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
        self.result_overrides: dict[str, object] = {}
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
        return await self.incoming.get()

    async def write_line(self, data: bytes) -> None:
        value = json.loads(data)
        self.writes.append(value)
        if "id" not in value:
            return
        method = value["method"]
        result = (
            self.initialize_result
            if method == "initialize"
            else self.result_overrides.get(method, self.responses[method])
        )
        response = {"id": value["id"], "result": result}
        self.incoming.put_nowait(json.dumps(response).encode("utf-8") + b"\n")

    async def close(self) -> None:
        self.close_count += 1
        self.close_started.set()
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
        self.assertTrue(opted_out)
        self.assertTrue(selected.isdisjoint(opted_out))
        self.assertEqual(session.generation, 1)
        self.assertEqual(
            session.capabilities.transports,
            frozenset({TransportCapability.INJECTED_BYTE_CHANNEL}),
        )
        self.assertTrue(all(session.capabilities.supports(item) for item in RequestCapability))
        with self.assertRaises(SessionStateError):
            await client.initialize(ClientIdentity("fixture", "1.0"))
        with self.assertRaises(SessionStateError):
            await client.initialize(ClientIdentity("changed", "2.0"))
        await session.close()
        self.assertEqual(peer.close_count, 1)

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
