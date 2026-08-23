from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import signal
import stat
import sys
import tempfile
import unittest
from contextlib import suppress
from pathlib import Path
from unittest import mock

from codex_app_server_client import (
    BinaryIdentity,
    InjectedTransport,
    JsonRpcFramingError,
    MessageTooLargeError,
    StdioTransport,
    TransportCapability,
    TransportCleanupError,
    TransportClosedError,
    TransportOwnership,
    TransportOwnershipError,
    TransportStartError,
    UnixSocketTransport,
)
from codex_app_server_client.transport import _ProcessByteChannel, _StreamByteChannel


def write_executable(directory: Path, body: str) -> BinaryIdentity:
    executable = directory / "codex-fixture"
    executable.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    resolved = executable.resolve()
    return BinaryIdentity(
        path=resolved,
        reported_version="0.147.0",
        sha256=hashlib.sha256(resolved.read_bytes()).hexdigest(),
    )


class MemoryChannel:
    def __init__(self) -> None:
        self.incoming: asyncio.Queue[bytes | BaseException] = asyncio.Queue()
        self.writes: list[bytes] = []
        self.close_count = 0
        self.close_completed = False
        self.close_error: BaseException | None = None
        self.close_gate: asyncio.Event | None = None
        self.close_started = asyncio.Event()
        self.write_error: BaseException | None = None
        self.write_gate: asyncio.Event | None = None
        self.write_started = asyncio.Event()
        self.active_writes = 0
        self.max_active_writes = 0

    async def read_line(self, *, max_bytes: int) -> bytes:
        item = await self.incoming.get()
        if isinstance(item, BaseException):
            raise item
        return item

    async def write_line(self, data: bytes) -> None:
        self.active_writes += 1
        self.max_active_writes = max(self.max_active_writes, self.active_writes)
        try:
            self.writes.append(data[: max(1, len(data) // 2)])
            self.write_started.set()
            await asyncio.sleep(0)
            if self.write_gate is not None:
                await self.write_gate.wait()
            if self.write_error is not None:
                raise self.write_error
            self.writes[-1] = data
        finally:
            self.active_writes -= 1

    async def close(self) -> None:
        self.close_count += 1
        self.close_started.set()
        if self.close_gate is not None:
            await self.close_gate.wait()
        if self.close_error is not None:
            raise self.close_error
        self.close_completed = True


class FakeWriter:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.closed = False
        self.drain_error: BaseException | None = None
        self.drain_gate: asyncio.Event | None = None
        self.close_error: BaseException | None = None
        self.wait_error: BaseException | None = None
        self.wait_gate: asyncio.Event | None = None
        self.wait_started = asyncio.Event()
        self.active_writes = 0
        self.max_active_writes = 0
        self._full_data = b""

    def write(self, data: bytes) -> None:
        self.active_writes += 1
        self.max_active_writes = max(self.max_active_writes, self.active_writes)
        self._full_data = data
        self.writes.append(data[: max(1, len(data) // 2)])

    async def drain(self) -> None:
        try:
            await asyncio.sleep(0)
            if self.drain_gate is not None:
                await self.drain_gate.wait()
            if self.drain_error is not None:
                raise self.drain_error
            if self.writes:
                self.writes[-1] = self._full_data
        finally:
            self.active_writes -= 1

    def close(self) -> None:
        self.closed = True
        if self.close_error is not None:
            raise self.close_error

    async def wait_closed(self) -> None:
        self.wait_started.set()
        if self.wait_gate is not None:
            await self.wait_gate.wait()
        if self.wait_error is not None:
            raise self.wait_error


class RefusingProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminate_count = 0
        self.kill_count = 0

    async def wait(self) -> int:
        await asyncio.Future()
        return 0

    def terminate(self) -> None:
        self.terminate_count += 1

    def kill(self) -> None:
        self.kill_count += 1


class EventProcess(RefusingProcess):
    def __init__(self) -> None:
        super().__init__()
        self.finished = asyncio.Event()

    async def wait(self) -> int:
        await self.finished.wait()
        self.returncode = 0
        return 0


class LookupProcess(RefusingProcess):
    def terminate(self) -> None:
        self.terminate_count += 1
        raise ProcessLookupError

    def kill(self) -> None:
        self.kill_count += 1
        raise ProcessLookupError


class WaitFailureAfterSignalProcess(RefusingProcess):
    def __init__(self) -> None:
        super().__init__()
        self.released = asyncio.Event()

    async def wait(self) -> int:
        await self.released.wait()
        raise RuntimeError("private-process-wait-content")

    def terminate(self) -> None:
        self.terminate_count += 1
        self.released.set()


class InjectedTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_channel_serializes_writes_and_closes_once(self) -> None:
        underlying = MemoryChannel()
        transport = InjectedTransport(underlying, ownership=TransportOwnership.OWNED)
        channel = await transport._open_channel()
        await asyncio.gather(*(channel.write_line(f'{{"n":{n}}}\n'.encode()) for n in range(4)))
        self.assertEqual(underlying.max_active_writes, 1)
        self.assertEqual(underlying.writes, [f'{{"n":{n}}}\n'.encode() for n in range(4)])
        await channel.close()
        await channel.close()
        self.assertEqual(underlying.close_count, 1)
        with self.assertRaises(TransportClosedError):
            await channel.write_line(b"{}\n")

    async def test_borrowed_close_cancels_active_read_without_closing_underlying(self) -> None:
        underlying = MemoryChannel()
        transport = InjectedTransport(underlying, ownership=TransportOwnership.BORROWED)
        channel = await transport._open_channel()
        read = asyncio.create_task(channel.read_line(max_bytes=32))
        await asyncio.sleep(0)
        await channel.close()
        with self.assertRaises(asyncio.CancelledError):
            await read
        self.assertEqual(underlying.close_count, 0)
        await underlying.incoming.put(b"still-owned-by-caller\n")
        self.assertEqual(await underlying.read_line(max_bytes=32), b"still-owned-by-caller\n")

    async def test_injected_read_enforces_bytes_framing_and_bound(self) -> None:
        for line, max_bytes, error in (
            (b"too-large\n", 8, MessageTooLargeError),
            (b"no-newline", 32, JsonRpcFramingError),
            (b"two\nlines\n", 32, JsonRpcFramingError),
            ("not-bytes", 32, JsonRpcFramingError),
        ):
            with self.subTest(line=line):
                underlying = MemoryChannel()
                transport = InjectedTransport(underlying, ownership=TransportOwnership.BORROWED)
                channel = await transport._open_channel()
                await underlying.incoming.put(line)  # type: ignore[arg-type]
                with self.assertRaises(error):
                    await channel.read_line(max_bytes=max_bytes)
                await channel.close()

    async def test_injected_partial_write_failure_is_typed_and_content_free(self) -> None:
        underlying = MemoryChannel()
        underlying.write_error = RuntimeError("private-write-content")
        channel = await InjectedTransport(
            underlying, ownership=TransportOwnership.OWNED
        )._open_channel()
        with self.assertRaises(TransportClosedError) as raised:
            await channel.write_line(b'{"request":"private"}\n')
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        self.assertNotIn("private", repr(vars(raised.exception)))
        with self.assertRaises(TransportClosedError):
            await channel.write_line(b"{}\n")
        await channel.close()

    async def test_cancelled_partial_write_fail_closes_before_next_writer(self) -> None:
        underlying = MemoryChannel()
        underlying.write_gate = asyncio.Event()
        channel = await InjectedTransport(
            underlying, ownership=TransportOwnership.OWNED
        )._open_channel()
        first = asyncio.create_task(channel.write_line(b'{"first":1}\n'))
        await underlying.write_started.wait()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        partial = list(underlying.writes)
        with self.assertRaises(TransportClosedError):
            await channel.write_line(b'{"second":2}\n')
        self.assertEqual(underlying.writes, partial)
        await channel.close()

    async def test_cancelled_owned_close_continues_and_retry_awaits_cleanup(self) -> None:
        underlying = MemoryChannel()
        underlying.close_gate = asyncio.Event()
        channel = await InjectedTransport(
            underlying, ownership=TransportOwnership.OWNED
        )._open_channel()
        first_close = asyncio.create_task(channel.close())
        await underlying.close_started.wait()
        first_close.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first_close
        self.assertFalse(underlying.close_completed)
        retry = asyncio.create_task(channel.close())
        await asyncio.sleep(0)
        self.assertFalse(retry.done())
        underlying.close_gate.set()
        await retry
        self.assertTrue(underlying.close_completed)
        self.assertEqual(underlying.close_count, 1)

    async def test_cancelled_owned_close_reports_eventual_failure_only_to_retry(self) -> None:
        underlying = MemoryChannel()
        underlying.close_gate = asyncio.Event()
        underlying.close_error = RuntimeError("private-cleanup-content")
        channel = await InjectedTransport(
            underlying, ownership=TransportOwnership.OWNED
        )._open_channel()
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        unexpected_contexts: list[dict[str, object]] = []
        loop.set_exception_handler(lambda _loop, context: unexpected_contexts.append(context))
        try:
            first_close = asyncio.create_task(channel.close())
            await underlying.close_started.wait()
            first_close.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first_close
            retry = asyncio.create_task(channel.close())
            await asyncio.sleep(0)
            self.assertFalse(retry.done())
            underlying.close_gate.set()
            with self.assertRaises(TransportCleanupError):
                await retry
            await asyncio.sleep(0)
            self.assertEqual(unexpected_contexts, [])
            self.assertEqual(underlying.close_count, 1)
        finally:
            loop.set_exception_handler(previous_handler)

    async def test_injected_eof_and_failed_owned_cleanup_are_discriminating(self) -> None:
        eof = MemoryChannel()
        eof_channel = await InjectedTransport(
            eof, ownership=TransportOwnership.BORROWED
        )._open_channel()
        await eof.incoming.put(EOFError("private-eof-content"))
        with self.assertRaises(TransportClosedError) as raised:
            await eof_channel.read_line(max_bytes=32)
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        await eof_channel.close()

        failed = MemoryChannel()
        failed.close_error = RuntimeError("private-cleanup-content")
        failed_channel = await InjectedTransport(
            failed, ownership=TransportOwnership.OWNED
        )._open_channel()
        with self.assertRaises(TransportCleanupError) as cleanup:
            await failed_channel.close()
        self.assertIsNone(cleanup.exception.__cause__)
        self.assertIsNone(cleanup.exception.__context__)
        with self.assertRaises(TransportCleanupError):
            await failed_channel.close()

    async def test_transport_instance_rejects_second_owner(self) -> None:
        transport = InjectedTransport(MemoryChannel(), ownership=TransportOwnership.BORROWED)
        channel = await transport._open_channel()
        with self.assertRaises(TransportOwnershipError):
            await transport._open_channel()
        await channel.close()

    def test_injected_constructor_requires_exact_ownership_and_channel(self) -> None:
        with self.assertRaises(TypeError):
            InjectedTransport(MemoryChannel(), ownership="owned")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            InjectedTransport(object(), ownership=TransportOwnership.OWNED)  # type: ignore[arg-type]


class StreamChannelTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_reads_multiple_buffered_lines_without_overread_loss(self) -> None:
        reader = asyncio.StreamReader()
        writer = FakeWriter()
        reader.feed_data(b"one\ntwo\n")
        channel = _StreamByteChannel(reader, writer)
        self.assertEqual(await channel.read_line(max_bytes=4), b"one\n")
        self.assertEqual(await channel.read_line(max_bytes=4), b"two\n")
        await channel.close()

    async def test_stream_serializes_writes_and_close_cancels_active_write(self) -> None:
        writer = FakeWriter()
        channel = _StreamByteChannel(asyncio.StreamReader(), writer)
        lines = [f'{{"n":{number}}}\n'.encode() for number in range(4)]
        await asyncio.gather(*(channel.write_line(line) for line in lines))
        self.assertEqual(writer.max_active_writes, 1)
        self.assertEqual(writer.writes, lines)

        writer.drain_gate = asyncio.Event()
        active = asyncio.create_task(channel.write_line(b'{"blocked":true}\n'))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await channel.close()
        with self.assertRaises(asyncio.CancelledError):
            await active
        self.assertEqual(writer.active_writes, 0)

    async def test_cancelled_stream_write_fail_closes_before_next_writer(self) -> None:
        writer = FakeWriter()
        writer.drain_gate = asyncio.Event()
        channel = _StreamByteChannel(asyncio.StreamReader(), writer)
        first = asyncio.create_task(channel.write_line(b'{"first":1}\n'))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        partial = list(writer.writes)
        with self.assertRaises(TransportClosedError):
            await channel.write_line(b'{"second":2}\n')
        self.assertEqual(writer.writes, partial)
        await channel.close()

    async def test_cancelled_process_close_continues_and_retry_reaps(self) -> None:
        writer = FakeWriter()
        writer.wait_gate = asyncio.Event()
        process = EventProcess()
        channel = _ProcessByteChannel(
            asyncio.StreamReader(),
            writer,
            process,  # type: ignore[arg-type]
        )
        first_close = asyncio.create_task(channel.close())
        await writer.wait_started.wait()
        first_close.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first_close
        retry = asyncio.create_task(channel.close())
        await asyncio.sleep(0)
        self.assertFalse(retry.done())
        writer.wait_gate.set()
        process.finished.set()
        await retry
        self.assertEqual(process.returncode, 0)
        self.assertEqual(process.terminate_count, 0)
        self.assertEqual(process.kill_count, 0)

    async def test_cancelled_stream_close_reports_eventual_failure_only_to_retry(self) -> None:
        writer = FakeWriter()
        writer.wait_gate = asyncio.Event()
        writer.wait_error = RuntimeError("private-cleanup-content")
        channel = _StreamByteChannel(asyncio.StreamReader(), writer)
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        unexpected_contexts: list[dict[str, object]] = []
        loop.set_exception_handler(lambda _loop, context: unexpected_contexts.append(context))
        try:
            first_close = asyncio.create_task(channel.close())
            await writer.wait_started.wait()
            first_close.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first_close
            retry = asyncio.create_task(channel.close())
            await asyncio.sleep(0)
            self.assertFalse(retry.done())
            writer.wait_gate.set()
            with self.assertRaises(TransportCleanupError):
                await retry
            await asyncio.sleep(0)
            self.assertEqual(unexpected_contexts, [])
        finally:
            loop.set_exception_handler(previous_handler)

    async def test_stream_bound_eof_partial_write_and_post_close(self) -> None:
        oversized_reader = asyncio.StreamReader()
        oversized_reader.feed_data(b"123456789\n")
        oversized = _StreamByteChannel(oversized_reader, FakeWriter())
        with self.assertRaises(MessageTooLargeError):
            await oversized.read_line(max_bytes=8)
        await oversized.close()

        eof_reader = asyncio.StreamReader()
        eof_reader.feed_data(b"partial")
        eof_reader.feed_eof()
        eof = _StreamByteChannel(eof_reader, FakeWriter())
        with self.assertRaises(TransportClosedError):
            await eof.read_line(max_bytes=16)
        await eof.close()

        partial_writer = FakeWriter()
        partial_writer.drain_error = RuntimeError("private-partial-write")
        partial = _StreamByteChannel(asyncio.StreamReader(), partial_writer)
        with self.assertRaises(TransportClosedError) as raised:
            await partial.write_line(b"complete-line\n")
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        await partial.close()
        with self.assertRaises(TransportClosedError):
            await partial.read_line(max_bytes=16)

    async def test_stream_failed_cleanup_is_typed_after_all_attempts(self) -> None:
        writer = FakeWriter()
        writer.close_error = RuntimeError("private-close")
        writer.wait_error = RuntimeError("private-wait")
        channel = _StreamByteChannel(asyncio.StreamReader(), writer)
        with self.assertRaises(TransportCleanupError) as raised:
            await channel.close()
        self.assertTrue(writer.closed)
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)

    async def test_process_cleanup_escalates_through_kill_and_fails_closed(self) -> None:
        process = RefusingProcess()
        channel = _ProcessByteChannel(
            asyncio.StreamReader(),
            FakeWriter(),
            process,  # type: ignore[arg-type]
        )
        with (
            mock.patch("codex_app_server_client.transport._PROCESS_EOF_GRACE_SECONDS", 0.001),
            mock.patch("codex_app_server_client.transport._PROCESS_TERMINATE_SECONDS", 0.001),
            mock.patch("codex_app_server_client.transport._PROCESS_KILL_SECONDS", 0.001),
            self.assertRaises(TransportCleanupError),
        ):
            await channel.close()
        self.assertEqual(process.terminate_count, 1)
        self.assertEqual(process.kill_count, 1)

    async def test_process_wait_failure_after_timeout_has_no_background_exception(self) -> None:
        process = WaitFailureAfterSignalProcess()
        channel = _ProcessByteChannel(
            asyncio.StreamReader(),
            FakeWriter(),
            process,  # type: ignore[arg-type]
        )
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        unexpected_contexts: list[dict[str, object]] = []
        loop.set_exception_handler(lambda _loop, context: unexpected_contexts.append(context))
        try:
            with (
                mock.patch("codex_app_server_client.transport._PROCESS_EOF_GRACE_SECONDS", 0.001),
                mock.patch("codex_app_server_client.transport._PROCESS_TERMINATE_SECONDS", 0.01),
                mock.patch("codex_app_server_client.transport._PROCESS_KILL_SECONDS", 0.01),
                self.assertRaises(TransportCleanupError) as raised,
            ):
                await channel.close()
            await asyncio.sleep(0)
            self.assertIsNone(raised.exception.__cause__)
            self.assertIsNone(raised.exception.__context__)
            self.assertNotIn("private-process-wait-content", repr(raised.exception))
            self.assertEqual(unexpected_contexts, [])
            self.assertEqual(process.terminate_count, 1)
            self.assertEqual(process.kill_count, 1)
        finally:
            loop.set_exception_handler(previous_handler)

    async def test_process_lookup_still_requires_bounded_reap_proof(self) -> None:
        process = LookupProcess()
        channel = _ProcessByteChannel(
            asyncio.StreamReader(),
            FakeWriter(),
            process,  # type: ignore[arg-type]
        )
        with (
            mock.patch("codex_app_server_client.transport._PROCESS_EOF_GRACE_SECONDS", 0.001),
            mock.patch("codex_app_server_client.transport._PROCESS_TERMINATE_SECONDS", 0.001),
            mock.patch("codex_app_server_client.transport._PROCESS_KILL_SECONDS", 0.001),
            self.assertRaises(TransportCleanupError),
        ):
            await channel.close()
        self.assertIsNone(process.returncode)
        self.assertEqual(process.terminate_count, 1)
        self.assertEqual(process.kill_count, 1)


class StdioTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_fixture_uses_exact_argv_echoes_and_reaps_child(self) -> None:
        body = (
            "import json, sys\n"
            "print(json.dumps(sys.argv[1:]), flush=True)\n"
            "for line in sys.stdin.buffer:\n"
            "    sys.stdout.buffer.write(line)\n"
            "    sys.stdout.buffer.flush()\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            identity = write_executable(Path(temporary), body)
            transport = StdioTransport(identity)
            channel = await transport._open_channel()
            process = channel._process  # type: ignore[attr-defined]
            argv = json.loads(await channel.read_line(max_bytes=128))
            self.assertEqual(argv, ["app-server", "--listen", "stdio://"])
            await channel.write_line(b'{"local":"fixture"}\n')
            self.assertEqual(await channel.read_line(max_bytes=128), b'{"local":"fixture"}\n')
            await channel.close()
            await channel.close()
            self.assertIsNotNone(process.returncode)
            with self.assertRaises(TransportClosedError):
                await channel.write_line(b"{}\n")
            with self.assertRaises(TransportOwnershipError):
                await transport._open_channel()

    @unittest.skipUnless(os.name == "posix", "signal fixture requires POSIX")
    async def test_stubborn_real_child_is_killed_and_reaped(self) -> None:
        body = (
            "import signal, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "print('ready', flush=True)\n"
            "while True:\n"
            "    time.sleep(1)\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            identity = write_executable(Path(temporary), body)
            channel = await StdioTransport(identity)._open_channel()
            self.assertEqual(await channel.read_line(max_bytes=16), b"ready\n")
            process = channel._process  # type: ignore[attr-defined]
            pid = process.pid
            with (
                mock.patch("codex_app_server_client.transport._PROCESS_EOF_GRACE_SECONDS", 0.02),
                mock.patch("codex_app_server_client.transport._PROCESS_TERMINATE_SECONDS", 0.02),
                mock.patch("codex_app_server_client.transport._PROCESS_KILL_SECONDS", 0.2),
            ):
                await channel.close()
            self.assertIsNotNone(process.returncode)
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    @unittest.skipUnless(os.name == "posix", "process-group fixture requires POSIX")
    async def test_owned_stdio_kills_stubborn_descendant_process_group(self) -> None:
        child_code = (
            "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"
        )
        body = (
            "import signal, subprocess, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}], "
            "stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, "
            "stderr=subprocess.DEVNULL)\n"
            "print(child.pid, flush=True)\n"
            "while True:\n"
            "    time.sleep(1)\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            identity = write_executable(Path(temporary), body)
            channel = await StdioTransport(identity)._open_channel()
            process = channel._process  # type: ignore[attr-defined]
            descendant_pid = int(await channel.read_line(max_bytes=32))
            try:
                with (
                    mock.patch(
                        "codex_app_server_client.transport._PROCESS_EOF_GRACE_SECONDS",
                        0.02,
                    ),
                    mock.patch(
                        "codex_app_server_client.transport._PROCESS_TERMINATE_SECONDS",
                        0.05,
                    ),
                    mock.patch("codex_app_server_client.transport._PROCESS_KILL_SECONDS", 1.0),
                ):
                    await channel.close()
                self.assertIsNotNone(process.returncode)
                with self.assertRaises(ProcessLookupError):
                    os.kill(descendant_pid, 0)
            finally:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)

    async def test_stale_unresolved_and_non_identity_inputs_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            StdioTransport("codex")  # type: ignore[arg-type]
        missing = BinaryIdentity(
            path=Path("/definitely/missing/codex"),
            reported_version="0.147.0",
            sha256="0" * 64,
        )
        with self.assertRaises(TransportStartError) as raised:
            await StdioTransport(missing)._open_channel()
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)

        with tempfile.TemporaryDirectory() as temporary:
            identity = write_executable(Path(temporary), "import sys\nsys.exit(0)\n")
            identity.path.write_text("changed", encoding="utf-8")
            with self.assertRaises(TransportStartError):
                await StdioTransport(identity)._open_channel()


@unittest.skipUnless(hasattr(asyncio, "start_unix_server"), "Unix sockets unavailable")
class UnixSocketTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_local_socket_echo_close_and_single_owner(self) -> None:
        completed = asyncio.Event()

        async def echo(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                while line := await reader.readline():
                    writer.write(line)
                    await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
                completed.set()

        with tempfile.TemporaryDirectory() as temporary:
            socket_path = Path(temporary) / "fixture.sock"
            server = await asyncio.start_unix_server(echo, path=socket_path)
            try:
                transport = UnixSocketTransport(socket_path)
                channel = await transport._open_channel()
                await channel.write_line(b'{"socket":"local"}\n')
                self.assertEqual(await channel.read_line(max_bytes=128), b'{"socket":"local"}\n')
                await channel.close()
                await asyncio.wait_for(completed.wait(), 1)
                with self.assertRaises(TransportOwnershipError):
                    await transport._open_channel()
            finally:
                server.close()
                await server.wait_closed()

    async def test_socket_path_and_connection_failures_are_bounded(self) -> None:
        for invalid in ("relative.sock", "/tmp/../unsafe.sock", "/" + "x" * 104):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                UnixSocketTransport(invalid)
        with self.assertRaises(TypeError):
            UnixSocketTransport(b"/tmp/bytes.sock")  # type: ignore[arg-type]
        with self.assertRaises(TransportStartError) as raised:
            await UnixSocketTransport("/tmp/definitely-missing-utils.sock")._open_channel()
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)


class PublicTransportContractTests(unittest.TestCase):
    def test_frozen_constructor_shapes_and_capabilities(self) -> None:
        stdio = inspect.signature(StdioTransport)
        unix = inspect.signature(UnixSocketTransport)
        injected = inspect.signature(InjectedTransport)
        self.assertEqual(list(stdio.parameters), ["binary"])
        self.assertEqual(list(unix.parameters), ["socket_path"])
        self.assertEqual(list(injected.parameters), ["channel", "ownership"])
        self.assertEqual(injected.parameters["ownership"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(StdioTransport.capability, TransportCapability.OWNED_STDIO)
        self.assertEqual(UnixSocketTransport.capability, TransportCapability.UNIX_SOCKET)
        self.assertEqual(InjectedTransport.capability, TransportCapability.INJECTED_BYTE_CHANNEL)

    def test_transport_source_has_no_shell_tcp_listener_or_singleton(self) -> None:
        import codex_app_server_client.transport as transport

        source = inspect.getsource(transport)
        self.assertNotIn("create_subprocess_shell", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("start_server", source)
        self.assertNotIn("start_unix_server", source)
        self.assertNotIn("WeakKeyDictionary", source)
        self.assertNotIn("ws://", source)


if __name__ == "__main__":
    unittest.main()
