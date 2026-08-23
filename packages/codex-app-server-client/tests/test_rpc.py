from __future__ import annotations

import asyncio
import gc
import inspect
import json
import unittest
from pathlib import Path

from codex_app_server_client import (
    BinaryIdentity,
    CorrelationError,
    JsonRpcFramingError,
    JsonRpcValidationError,
    MessageTooLargeError,
    RemoteRpcError,
    RequestCapability,
    RequestLimitError,
    inspect_compatibility,
)
from codex_app_server_client.rpc import _RpcEngine, _RpcLimits


def fake_identity() -> BinaryIdentity:
    return BinaryIdentity(
        path=Path("/nonexistent/codex"), reported_version="0.147.0", sha256="0" * 64
    )


class DeterministicPeer:
    """A process- and socket-free byte-channel peer fixture."""

    def __init__(self) -> None:
        self.incoming: asyncio.Queue[bytes | BaseException] = asyncio.Queue()
        self.outgoing: asyncio.Queue[bytes] = asyncio.Queue()
        self.writes: list[bytes] = []
        self.closed = False
        self.write_error: BaseException | None = None
        self.response_during_write: dict[str, object] | None = None

    async def read_line(self, *, max_bytes: int) -> bytes:
        item = await self.incoming.get()
        if isinstance(item, BaseException):
            raise item
        return item

    async def write_line(self, data: bytes) -> None:
        if self.response_during_write is not None:
            request = json.loads(data)
            response = {"id": request["id"], **self.response_during_write}
            self.incoming.put_nowait(json.dumps(response).encode() + b"\n")
            await asyncio.sleep(0)
        if self.write_error is not None:
            error, self.write_error = self.write_error, None
            raise error
        if self.closed:
            raise EOFError("peer is closed")
        self.writes.append(data)
        await self.outgoing.put(data)

    async def close(self) -> None:
        self.closed = True

    async def request(self) -> dict[str, object]:
        return json.loads(await self.outgoing.get())

    async def respond(self, value: object) -> None:
        await self.incoming.put(json.dumps(value, separators=(",", ":")).encode("utf-8") + b"\n")

    async def raw(self, line: bytes) -> None:
        await self.incoming.put(line)

    async def fail(self, error: BaseException) -> None:
        await self.incoming.put(error)


class RpcEngineTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compatibility = inspect_compatibility(fake_identity())

    async def asyncSetUp(self) -> None:
        self.engines: list[_RpcEngine] = []

    async def asyncTearDown(self) -> None:
        for engine in self.engines:
            await engine.close()

    def engine(self, limits: _RpcLimits | None = None) -> tuple[_RpcEngine, DeterministicPeer]:
        peer = DeterministicPeer()
        engine = _RpcEngine(peer, self.compatibility, limits=limits)
        self.engines.append(engine)
        return engine, peer

    async def test_successful_call_uses_integer_id_and_cleans_pending(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(
            engine.call(RequestCapability.THREAD_READ, {"threadId": "local-fixture"})
        )
        request = await peer.request()
        self.assertIs(type(request["id"]), int)
        self.assertEqual(request["method"], "thread/read")
        await peer.respond({"id": request["id"], "result": {"thread": "opaque"}})
        self.assertEqual(await call, {"thread": "opaque"})
        self.assertEqual(engine.pending_count, 0)

    async def test_concurrent_calls_correlate_out_of_order_exactly_once(self) -> None:
        engine, peer = self.engine()
        first = asyncio.create_task(engine.call(RequestCapability.THREAD_LIST, {"limit": 1}))
        second = asyncio.create_task(engine.call(RequestCapability.REVIEW_START, {"x": 2}))
        requests = [await peer.request(), await peer.request()]
        by_method = {request["method"]: request for request in requests}
        await peer.respond({"id": by_method["review/start"]["id"], "result": {"order": "second"}})
        await peer.respond({"id": by_method["thread/list"]["id"], "result": {"order": "first"}})
        self.assertEqual(await first, {"order": "first"})
        self.assertEqual(await second, {"order": "second"})
        self.assertEqual(engine.pending_count, 0)

    async def test_valid_remote_error_is_typed_and_does_not_retain_content(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.TURN_INTERRUPT, {}))
        request = await peer.request()
        await peer.respond(
            {
                "id": request["id"],
                "error": {"code": -32001, "message": "unavailable", "data": {"secret": 1}},
            }
        )
        with self.assertRaises(RemoteRpcError) as raised:
            await call
        self.assertEqual(raised.exception.request_id, request["id"])
        self.assertEqual(raised.exception.code, -32001)
        self.assertTrue(raised.exception.has_data)
        self.assertFalse(hasattr(raised.exception, "data"))
        self.assertFalse(hasattr(raised.exception, "remote_message"))
        self.assertNotIn("unavailable", str(raised.exception))
        self.assertEqual(engine.pending_count, 0)

    async def test_pending_bound_rejects_before_second_write(self) -> None:
        engine, peer = self.engine(_RpcLimits(max_pending_calls=1))
        first = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        request = await peer.request()
        with self.assertRaises(RequestLimitError):
            await engine.call(RequestCapability.THREAD_LIST, {})
        self.assertEqual(len(peer.writes), 1)
        await peer.respond({"id": request["id"], "result": {}})
        await first

    async def test_outbound_message_bound_rejects_and_cleans_pending(self) -> None:
        engine, peer = self.engine(_RpcLimits(max_message_bytes=96))
        with self.assertRaises(MessageTooLargeError):
            await engine.call(RequestCapability.THREAD_START, {"text": "x" * 200})
        self.assertEqual(peer.writes, [])
        self.assertEqual(engine.pending_count, 0)

    async def test_outbound_non_json_value_rejects_and_cleans_pending(self) -> None:
        engine, peer = self.engine()
        with self.assertRaises(JsonRpcValidationError):
            await engine.call(RequestCapability.THREAD_START, {"invalid": object()})
        self.assertEqual(peer.writes, [])
        self.assertEqual(engine.pending_count, 0)

    async def test_timeout_handoff_cleans_pending_and_consumes_one_late_response(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}, timeout=0.01))
        request = await peer.request()
        with self.assertRaises(TimeoutError):
            await call
        self.assertEqual(engine.pending_count, 0)
        await peer.respond({"id": request["id"], "result": {"late": True}})
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertIsNone(engine.failure)

    async def test_caller_cancellation_cleans_pending(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        request = await peer.request()
        call.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await call
        self.assertEqual(engine.pending_count, 0)
        await peer.respond({"id": request["id"], "result": {"late": True}})
        await asyncio.sleep(0)
        self.assertIsNone(engine.failure)

    async def test_ready_success_response_racing_cancellation_keeps_engine_healthy(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        request = await peer.request()
        peer.incoming.put_nowait(
            json.dumps({"id": request["id"], "result": {"ready": True}}).encode() + b"\n"
        )
        call.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await call
        await asyncio.sleep(0)
        self.assertIsNone(engine.failure)
        self.assertEqual(engine.pending_count, 0)

    async def test_ready_remote_error_racing_cancellation_keeps_engine_healthy(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        request = await peer.request()
        peer.incoming.put_nowait(
            json.dumps(
                {
                    "id": request["id"],
                    "error": {"code": -32001, "message": "private-response-content"},
                }
            ).encode()
            + b"\n"
        )
        call.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await call
        await asyncio.sleep(0)
        self.assertIsNone(engine.failure)
        self.assertEqual(engine.pending_count, 0)

    async def test_peer_closure_fails_every_pending_call_without_leak(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        await peer.request()
        await peer.fail(EOFError("closed"))
        with self.assertRaises(JsonRpcFramingError):
            await call
        await engine.wait_closed()
        self.assertEqual(engine.pending_count, 0)
        self.assertTrue(peer.closed)

    async def test_read_failure_does_not_retain_channel_content(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        await peer.request()
        await peer.fail(RuntimeError("private-read-channel-content"))
        with self.assertRaises(JsonRpcFramingError) as raised:
            await call
        self.assert_exception_graph_excludes(raised.exception, "private-read-channel-content")

    async def test_unmatched_id_is_a_fatal_correlation_error(self) -> None:
        engine, peer = self.engine()
        await engine.start()
        await peer.respond({"id": 99, "result": {}})
        await engine.wait_closed()
        self.assertIsInstance(engine.failure, CorrelationError)
        self.assertIn("unmatched", str(engine.failure))

    async def test_duplicate_id_is_detected_after_exactly_one_resolution(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        request = await peer.request()
        response = {"id": request["id"], "result": {"once": True}}
        await peer.respond(response)
        self.assertEqual(await call, {"once": True})
        await peer.respond(response)
        await engine.wait_closed()
        self.assertIsInstance(engine.failure, CorrelationError)
        self.assertIn("duplicate", str(engine.failure))
        self.assertEqual(engine.pending_count, 0)

    async def test_non_integer_and_boolean_ids_are_rejected(self) -> None:
        for invalid_id in ("1", True, 0, -1):
            with self.subTest(invalid_id=invalid_id):
                engine, peer = self.engine()
                call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
                await peer.request()
                await peer.respond({"id": invalid_id, "result": {}})
                with self.assertRaises(JsonRpcValidationError):
                    await call
                self.assertEqual(engine.pending_count, 0)

    async def test_invalid_response_schema_fails_pending_without_leak(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        request = await peer.request()
        await peer.respond({"id": request["id"]})
        with self.assertRaises(JsonRpcValidationError):
            await call
        self.assertEqual(engine.pending_count, 0)

    async def test_malformed_json_object_and_duplicate_keys_are_rejected(self) -> None:
        lines = (
            b"{not-json}\n",
            b"[]\n",
            b'{"id":1,"id":1,"result":{}}\n',
            b'{"id":1,"result":NaN}\n',
            b'{"id":1,"result":{}}',
        )
        for line in lines:
            with self.subTest(line=line):
                engine, peer = self.engine()
                call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
                await peer.request()
                await peer.raw(line)
                with self.assertRaises((JsonRpcFramingError, JsonRpcValidationError)):
                    await call
                self.assertEqual(engine.pending_count, 0)

    async def test_framing_failure_does_not_retain_inbound_content(self) -> None:
        engine, peer = self.engine()
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        await peer.request()
        await peer.raw(b'{"private-response-content"\n')
        with self.assertRaises(JsonRpcFramingError) as raised:
            await call
        self.assert_exception_graph_excludes(raised.exception, "private-response-content")

    async def test_outbound_validation_does_not_retain_request_content(self) -> None:
        class PrivateValue:
            def __repr__(self) -> str:
                return "private-request-content"

        engine, _ = self.engine()
        with self.assertRaises(JsonRpcValidationError) as raised:
            await engine.call(RequestCapability.THREAD_START, {"invalid": PrivateValue()})
        self.assert_exception_graph_excludes(raised.exception, "private-request-content")

    async def test_write_failure_is_content_free_and_has_no_unretrieved_future(self) -> None:
        engine, peer = self.engine()
        peer.write_error = RuntimeError("private-channel-content")
        loop = asyncio.get_running_loop()
        contexts: list[dict[str, object]] = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: contexts.append(context))
        try:
            with self.assertRaises(JsonRpcFramingError) as raised:
                await engine.call(RequestCapability.THREAD_READ, {})
            gc.collect()
            await asyncio.sleep(0)
        finally:
            loop.set_exception_handler(previous_handler)
        self.assert_exception_graph_excludes(raised.exception, "private-channel-content")
        self.assertEqual(engine.pending_count, 0)
        self.assertFalse(
            any("Future exception was never retrieved" in str(item) for item in contexts),
            contexts,
        )

    async def test_partial_write_success_race_consumes_completed_future(self) -> None:
        engine, peer = self.engine()
        peer.response_during_write = {"result": {"delivered": True}}
        peer.write_error = RuntimeError("drain failed")
        contexts = await self.assert_failed_write_has_no_orphan(engine)
        self.assertEqual(engine.pending_count, 0)
        self.assertFalse(
            any("Future exception was never retrieved" in str(item) for item in contexts),
            contexts,
        )

    async def test_partial_write_remote_error_race_consumes_completed_future(self) -> None:
        engine, peer = self.engine()
        peer.response_during_write = {"error": {"code": -32002, "message": "already resolved"}}
        peer.write_error = RuntimeError("drain failed")
        contexts = await self.assert_failed_write_has_no_orphan(engine)
        self.assertEqual(engine.pending_count, 0)
        self.assertFalse(
            any("Future exception was never retrieved" in str(item) for item in contexts),
            contexts,
        )

    async def test_oversized_inbound_line_fails_pending_without_leak(self) -> None:
        engine, peer = self.engine(_RpcLimits(max_message_bytes=96))
        call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
        request = await peer.request()
        line = json.dumps({"id": request["id"], "result": {"text": "x" * 200}}).encode() + b"\n"
        await peer.raw(line)
        with self.assertRaises(MessageTooLargeError):
            await call
        self.assertEqual(engine.pending_count, 0)

    async def test_request_id_space_exhausts_instead_of_double_resolving(self) -> None:
        engine, peer = self.engine(_RpcLimits(max_pending_calls=1, max_request_id=2))
        for expected_id in (1, 2):
            call = asyncio.create_task(engine.call(RequestCapability.THREAD_READ, {}))
            request = await peer.request()
            self.assertEqual(request["id"], expected_id)
            await peer.respond({"id": request["id"], "result": {}})
            await call
        with self.assertRaises(RequestLimitError):
            await engine.call(RequestCapability.THREAD_READ, {})

    def test_rpc_core_has_no_concrete_transport_dependency(self) -> None:
        import codex_app_server_client.rpc as rpc

        source = inspect.getsource(rpc)
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("import socket", source)
        self.assertNotIn("create_subprocess", source)
        self.assertNotIn("open_unix_connection", source)

    def assert_exception_graph_excludes(self, error: BaseException, secret: str) -> None:
        seen: set[int] = set()
        stack: list[BaseException] = [error]
        while stack:
            current = stack.pop()
            if id(current) in seen:
                continue
            seen.add(id(current))
            self.assertNotIn(secret, repr(current))
            self.assertNotIn(secret, repr(current.args))
            self.assertNotIn(secret, repr(vars(current)))
            if current.__cause__ is not None:
                stack.append(current.__cause__)
            if current.__context__ is not None:
                stack.append(current.__context__)

    async def assert_failed_write_has_no_orphan(
        self, engine: _RpcEngine
    ) -> list[dict[str, object]]:
        loop = asyncio.get_running_loop()
        contexts: list[dict[str, object]] = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: contexts.append(context))
        try:
            with self.assertRaises(JsonRpcFramingError):
                await engine.call(RequestCapability.THREAD_READ, {})
            gc.collect()
            await asyncio.sleep(0)
        finally:
            loop.set_exception_handler(previous_handler)
        return contexts


class RpcLimitTests(unittest.TestCase):
    def test_invalid_bounds_fail_before_use(self) -> None:
        for kwargs in (
            {"max_message_bytes": 1},
            {"max_pending_calls": 0},
            {"max_request_id": 0},
            {"max_pending_calls": 3, "max_request_id": 2},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                _RpcLimits(**kwargs)


if __name__ == "__main__":
    unittest.main()
