"""Neutral framed peers; no downstream runtime or model calls."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

import codex_app_server_client as legacy
from codex_app_server_client import v0_156_1 as local
from codex_app_server_client import v0_162_1 as modern
from test_versioned_session import OPERATIONS, fixture, identity, peer_for


def frame(payload, opcode=1, final=True):
    size = len(payload)
    header = bytes([(128 if final else 0) | opcode])
    if size < 126:
        header += bytes([size])
    elif size < 65536:
        header += b"\x7e" + struct.pack("!H", size)
    else:
        header += b"\x7f" + struct.pack("!Q", size)
    return header + payload


async def client_frame(reader):
    first, second = await reader.readexactly(2)
    assert first & 128 and second & 128
    size = second & 127
    if size == 126:
        size = struct.unpack("!H", await reader.readexactly(2))[0]
    elif size == 127:
        size = struct.unpack("!Q", await reader.readexactly(8))[0]
    assert size <= 8 * 1024 * 1024
    mask = await reader.readexactly(4)
    payload = await reader.readexactly(size)
    return first & 15, bytes(value ^ mask[index % 4] for index, value in enumerate(payload))


class LocalWebSocketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="ws-")
        self.addCleanup(self.directory.cleanup)
        self.tasks = set()
        self.writers = []
        self.peers = []
        self.received = []
        self.sent = None
        self.bad_upgrade = False
        self.socket = Path(self.directory.name) / "control.sock"
        self.server = await asyncio.start_unix_server(self.handle, path=self.socket)
        self.addAsyncCleanup(self.cleanup)

    async def cleanup(self):
        self.server.close()
        await self.server.wait_closed()
        for writer in self.writers:
            writer.close()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def handle(self, reader, writer):
        self.tasks.add(asyncio.current_task())
        self.writers.append(writer)
        peer = peer_for(local)
        peer.responses["thread/turns/list"] = fixture(local, "ThreadTurnsListResponse")
        peer.responses["thread/items/list"] = fixture(local, "ThreadItemsListResponse")
        self.peers.append(peer)
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            key = next(
                line.split(b":", 1)[1].strip()
                for line in request.split(b"\r\n")
                if line.lower().startswith(b"sec-websocket-key:")
            )
            accept = base64.b64encode(
                hashlib.sha1(
                    key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11", usedforsecurity=False
                ).digest()
            )
            if self.bad_upgrade:
                accept = b"invalid"
            writer.write(
                b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                b"Connection: Upgrade\r\nSec-WebSocket-Accept: " + accept + b"\r\n\r\n"
            )
            if self.sent is not None:
                writer.write(self.sent)
            await writer.drain()
            while True:
                opcode, payload = await client_frame(reader)
                self.received.append((opcode, payload))
                if self.sent is not None or opcode != 1:
                    continue
                await peer.write_line(payload + b"\n")
                while not peer.incoming.empty():
                    writer.write(frame((await peer.incoming.get()).rstrip(b"\n")))
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()

    async def test_framed_typed_session_pagination_and_replacement(self):
        client = await local.AppServerClient.connect(
            local.LocalWebSocketTransport(self.socket), local.inspect_compatibility(identity(local))
        )
        self.addAsyncCleanup(client.close)
        session = await client.initialize(local.ClientIdentity("neutral", "1"))
        for coverage in ("full", "summary", "notLoaded"):
            result = await session.list_turns(
                local.ThreadTurnsListParams(threadId="selected", limit=2, itemsView=coverage)
            )
            self.assertIs(type(result), local.ThreadTurnsListResponse)
            self.assertEqual(self.peers[-1].writes[-1]["params"]["threadId"], "selected")

            self.assertEqual(self.peers[-1].writes[-1]["params"]["itemsView"], coverage)
        before = len(self.peers[-1].writes)
        for params in (
            dict(threadId="selected"),
            dict(threadId="selected", limit=101, itemsView="full"),
        ):
            with self.assertRaises(ValueError):
                await session.list_turns(local.ThreadTurnsListParams(**params))
        self.assertEqual(len(self.peers[-1].writes), before)
        self.writers[-1].close()
        await self.writers[-1].wait_closed()
        with self.assertRaises(local.AppServerClientError):
            await session.list_turns(
                local.ThreadTurnsListParams(threadId="selected", limit=1, itemsView="full"),
                timeout=1,
            )
        replacement = await client.replace(local.LocalWebSocketTransport(self.socket))
        self.assertEqual(replacement.generation, 2)
        await client.close()
        self.assertTrue(self.server.is_serving())
        self.assertEqual(len(self.peers), 2)

    async def test_dispatch_guard_runs_after_each_write_lock(self):
        client = await local.AppServerClient.connect(
            local.LocalWebSocketTransport(self.socket), local.inspect_compatibility(identity(local))
        )
        self.addAsyncCleanup(client.close)
        session = await client.initialize(local.ClientIdentity("neutral", "1"))
        for lock in (client._engine._write_lock, client._engine._channel._write_lock):
            with self.subTest(lock=lock):
                times = []
                clock = [100]

                def check(times=times, clock=clock):
                    times.append(clock[0])
                    if clock[0] >= 112:
                        raise ValueError("expired secret detail")

                await lock.acquire()

                async def invoke(check=check):
                    with local.dispatch_guard(check):
                        return await session.steer_turn(
                            local.TurnSteerParams(
                                threadId="selected",
                                expectedTurnId="turn-selected",
                                input=[{"type": "text", "text": "bounded input"}],
                            )
                        )

                task = asyncio.create_task(invoke())
                # Let model validation, RPC registration and the write task run.
                for _ in range(10):
                    await asyncio.sleep(0)
                self.assertFalse(task.done())
                self.assertEqual(times, [])
                before = len(self.peers[-1].writes)
                clock[0] = 115
                lock.release()
                with self.assertRaises(local.DispatchRejectedError) as error:
                    await task
                self.assertNotIn("secret", str(error.exception))
                self.assertEqual(times, [115])
                self.assertEqual(len(self.peers[-1].writes), before)
                self.assertEqual(client._engine.pending_count, 0)
        # Rejection does not poison the borrowed session or leak the guard.
        await session.list_threads(local.ThreadListParams(limit=1))

    async def test_typed_item_pages_preserve_native_cursor_and_reject_unbounded_reads(self):
        client = await local.AppServerClient.connect(
            local.LocalWebSocketTransport(self.socket), local.inspect_compatibility(identity(local))
        )
        self.addAsyncCleanup(client.close)
        session = await client.initialize(local.ClientIdentity("neutral", "1"))
        params = local.ThreadItemsListParams(
            threadId="selected",
            turnId="turn-selected",
            cursor="opaque-native-cursor",
            limit=16,
            sortDirection="desc",
        )
        result = await session.list_items(params)
        self.assertIs(type(result), local.ThreadItemsListResponse)
        self.assertEqual(self.peers[-1].writes[-1]["params"], params.to_dict())
        self.assertTrue(session.capabilities.supports(local.RequestCapability.THREAD_ITEMS_LIST))
        before = len(self.peers[-1].writes)
        for fields in (
            dict(threadId="selected"),
            dict(threadId="selected", limit=101, sortDirection="desc"),
            dict(threadId="selected", limit=2),
        ):
            with self.assertRaises(ValueError):
                await session.list_items(local.ThreadItemsListParams(**fields))
        self.assertEqual(len(self.peers[-1].writes), before)
        for api in (legacy, modern):
            self.assertFalse(hasattr(api.AppServerSession, "list_items"))
            self.assertFalse(
                api.inspect_compatibility(identity(api)).features.supports(
                    local.RequestCapability.THREAD_ITEMS_LIST
                )
            )

    async def test_cancelled_guarded_request_stays_unsent_after_queue_release(self):
        client = await local.AppServerClient.connect(
            local.LocalWebSocketTransport(self.socket), local.inspect_compatibility(identity(local))
        )
        self.addAsyncCleanup(client.close)
        session = await client.initialize(local.ClientIdentity("neutral", "1"))
        lock = client._engine._channel._write_lock
        await lock.acquire()

        async def invoke():
            with local.dispatch_guard(lambda: None):
                await session.list_threads(local.ThreadListParams(limit=1))

        task = asyncio.create_task(invoke())
        for _ in range(10):
            await asyncio.sleep(0)
        before = len(self.peers[-1].writes)
        task.cancel()
        try:
            with self.assertRaises(asyncio.CancelledError):
                await task
        finally:
            lock.release()
        await client._engine.wait_quiescent()
        self.assertEqual(len(self.peers[-1].writes), before)

    async def test_guard_rejects_unsupported_injected_channel_without_writes(self):
        peer = peer_for(local)
        client = await local.AppServerClient.connect(
            local.InjectedTransport(peer, ownership=local.TransportOwnership.BORROWED),
            local.inspect_compatibility(identity(local)),
        )
        self.addAsyncCleanup(client.close)
        session = await client.initialize(local.ClientIdentity("neutral", "1"))
        before = len(peer.writes)
        with local.dispatch_guard(lambda: None), self.assertRaises(local.DispatchRejectedError):
            await session.list_threads(local.ThreadListParams(limit=1))
        self.assertEqual(len(peer.writes), before)

    async def test_stream_guard_checks_after_channel_lock(self):
        from types import SimpleNamespace

        from codex_app_server_client.transport import _StreamByteChannel

        writes = []
        channel = _StreamByteChannel(asyncio.StreamReader(), SimpleNamespace(write=writes.append))

        async def invalid_async_check():
            pass

        with self.assertRaises(local.DispatchRejectedError):
            await channel.guarded_write_line(b"{}\n", invalid_async_check)
        self.assertEqual(writes, [])

    async def test_legacy_profiles_reject_new_capabilities_before_io(self):
        for api in (legacy, modern):
            compatibility = api.inspect_compatibility(identity(api))
            self.assertFalse(
                compatibility.features.supports(local.RequestCapability.THREAD_TURNS_LIST)
            )
            self.assertFalse(
                compatibility.features.supports(local.TransportCapability.LOCAL_WEBSOCKET)
            )
            transport = local.LocalWebSocketTransport(self.socket)
            with self.assertRaises(api.UnsupportedFeatureError):
                await api.AppServerClient.connect(transport, compatibility)
            self.assertFalse(transport._claimed)
            self.assertFalse(hasattr(api.AppServerSession, "list_turns"))
        self.assertEqual(self.peers, [])

    async def test_exact_156_models_and_version_rejection(self):
        peer = peer_for(local)
        client = await local.AppServerClient.connect(
            local.InjectedTransport(peer, ownership=local.TransportOwnership.OWNED),
            local.inspect_compatibility(identity(local)),
        )
        self.addAsyncCleanup(client.close)
        session = await client.initialize(local.ClientIdentity("neutral", "1"))
        for operation, method, params_name, response_name in OPERATIONS:
            with self.subTest(method=method):
                result = await getattr(session, operation)(
                    getattr(local, params_name).from_dict(fixture(local, params_name))
                )
                self.assertIs(type(result), getattr(local, response_name))
        with self.assertRaises(TypeError):
            await session.read_thread(modern.ThreadReadParams(threadId="foreign"))
        with self.assertRaises(local.CodexVersionError):
            local.inspect_compatibility(identity(modern))

    async def test_fragments_ping_and_masked_client_output(self):
        self.sent = (
            frame(b"hello", final=False) + frame(b"ping", opcode=9) + frame(b"world", opcode=0)
        )
        channel = await local.LocalWebSocketTransport(self.socket)._open_channel()
        self.addAsyncCleanup(channel.close)
        self.assertEqual(await channel.read_line(max_bytes=11), b"helloworld\n")
        await channel.write_line(b'{"method":"test"}\n')
        await asyncio.sleep(0.01)
        self.assertIn((10, b"ping"), self.received)
        self.assertIn((1, b'{"method":"test"}'), self.received)

    async def test_invalid_frames_and_bounds_fail_closed(self):
        cases = [
            b"\x81\x80",
            b"\xc1\x00",
            b"\x82\x00",
            b"\x00\x00",
            b"\x09\x00",
            b"\x81\x7e\x00\x01",
            frame(b"\xff"),
            frame(struct.pack("!H", 1005), opcode=8),
            frame(b"", opcode=10) * 1024,
        ]
        for raw in cases:
            with self.subTest(raw=raw[:8]):
                self.sent = raw
                channel = await local.LocalWebSocketTransport(self.socket)._open_channel()
                try:
                    with self.assertRaises(local.JsonRpcFramingError):
                        await channel.read_line(max_bytes=100)
                    with self.assertRaises(local.TransportClosedError):
                        await channel.read_line(max_bytes=100)
                finally:
                    await channel.close()
        self.sent = b"\x81\x7e\x01\x00"
        channel = await local.LocalWebSocketTransport(self.socket)._open_channel()
        try:
            with self.assertRaises(local.MessageTooLargeError):
                await channel.read_line(max_bytes=100)
        finally:
            await channel.close()

    async def test_upgrade_and_address_rejection(self):
        self.bad_upgrade = True
        with self.assertRaises(local.TransportStartError):
            await local.LocalWebSocketTransport(self.socket)._open_channel()
        for path in ("wss://example.test", "relative.sock", "/a/../socket"):
            with self.assertRaises(ValueError):
                local.LocalWebSocketTransport(path)
