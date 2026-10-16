"""Neutral guarded injected channels, with no process or model calls."""

import asyncio
import unittest

from codex_app_server_client import v0_156_1 as api
from test_versioned_session import identity, peer_for


class GuardedPeer:
    def __init__(self):
        self.peer = peer_for(api)
        self.lock = asyncio.Lock()

    async def read_line(self, *, max_bytes):
        return await self.peer.read_line(max_bytes=max_bytes)

    async def write_line(self, data):
        await self.peer.write_line(data)

    async def guarded_write_line(self, data, check):
        async with self.lock:
            check()
            await self.peer.write_line(data)

    async def close(self):
        await self.peer.close()


class InjectedDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def connect(self, peer):
        client = await api.AppServerClient.connect(
            api.InjectedTransport(peer, ownership=api.TransportOwnership.OWNED),
            api.inspect_compatibility(identity(api)),
        )
        self.addAsyncCleanup(client.close)
        return client, await client.initialize(api.ClientIdentity("neutral", "1"))

    async def test_guard_rechecks_after_rpc_wrapper_and_injected_channel_locks(self):
        peer = GuardedPeer()
        client, session = await self.connect(peer)
        for lock in (client._engine._write_lock, client._engine._channel._write_lock, peer.lock):
            clock = [1]

            def check(clock=clock):
                if clock[0] > 1:
                    raise ValueError("expired private detail")

            async def request(check=check):
                with api.dispatch_guard(check):
                    return await session.read_thread(api.ThreadReadParams(threadId="exact"))

            await lock.acquire()
            before = len(peer.peer.writes)
            task = asyncio.create_task(request())
            for _ in range(10):
                await asyncio.sleep(0)
            self.assertFalse(task.done())
            clock[0] = 2
            lock.release()
            with self.assertRaises(api.DispatchRejectedError) as raised:
                await task
            self.assertNotIn("private", str(raised.exception))
            self.assertEqual(len(peer.peer.writes), before)
            self.assertEqual(client._engine.pending_count, 0)
            await session.read_thread(api.ThreadReadParams(threadId="still-usable"))

    async def test_plain_injected_peer_rejects_guarded_request_before_write(self):
        peer = peer_for(api)
        _, session = await self.connect(peer)
        before = len(peer.writes)
        with api.dispatch_guard(lambda: None), self.assertRaises(api.DispatchRejectedError):
            await session.read_thread(api.ThreadReadParams(threadId="exact"))
        self.assertEqual(len(peer.writes), before)
        await session.read_thread(api.ThreadReadParams(threadId="still-usable"))

    async def test_cancelled_request_never_writes_after_injected_lock_release(self):
        peer = GuardedPeer()
        _, session = await self.connect(peer)
        await peer.lock.acquire()

        async def request():
            with api.dispatch_guard(lambda: None):
                return await session.read_thread(api.ThreadReadParams(threadId="cancelled"))

        before = len(peer.peer.writes)
        task = asyncio.create_task(request())
        for _ in range(10):
            await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises((asyncio.CancelledError, api.CallCancelledError)):
            await task
        peer.lock.release()
        for _ in range(10):
            await asyncio.sleep(0)
        self.assertEqual(len(peer.peer.writes), before)
