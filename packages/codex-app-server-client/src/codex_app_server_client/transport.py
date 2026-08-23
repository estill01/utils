"""Selected local byte transports with explicit, single-use ownership."""

from __future__ import annotations

import asyncio
import hashlib
import os
import signal
from contextlib import suppress
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from .compatibility import PINNED_PROTOCOL, BinaryIdentity
from .errors import (
    JsonRpcFramingError,
    MessageTooLargeError,
    TransportCleanupError,
    TransportClosedError,
    TransportOwnershipError,
    TransportStartError,
)
from .rpc import ByteChannel
from .surface import TransportCapability

_READ_CHUNK_BYTES = 64 * 1024
_STREAM_BUFFER_LIMIT = 8 * 1024 * 1024 + 1
_PROCESS_EOF_GRACE_SECONDS = 0.25
_PROCESS_TERMINATE_SECONDS = 1.0
_PROCESS_KILL_SECONDS = 1.0
_STREAM_CLOSE_SECONDS = 1.0
_PORTABLE_UNIX_PATH_BYTES = 103
_SIGNAL_TERMINATE = getattr(signal, "SIGTERM", 15)
_SIGNAL_KILL = getattr(signal, "SIGKILL", 9)


class TransportOwnership(StrEnum):
    OWNED = "owned"
    BORROWED = "borrowed"


class ClientTransport(Protocol):
    """Closed package transport input used by the later client owner."""

    capability: TransportCapability

    async def _open_channel(self) -> ByteChannel:
        """Claim this transport instance and return its one byte channel."""


def _validate_write_line(data: bytes) -> None:
    if not isinstance(data, bytes):
        raise TypeError("byte-channel writes require bytes")
    if not data.endswith(b"\n") or b"\n" in data[:-1]:
        raise JsonRpcFramingError("byte-channel write must be one newline-terminated record")


def _consume_task_exception(task: asyncio.Task[Any]) -> None:
    if not task.cancelled():
        with suppress(Exception):
            task.exception()


class _StreamByteChannel:
    """Bounded JSON-line behavior over one asyncio reader/writer pair."""

    def __init__(self, reader: asyncio.StreamReader, writer: Any) -> None:
        self._reader = reader
        self._writer = writer
        self._buffer = bytearray()
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._close_lock = asyncio.Lock()
        self._active_read: asyncio.Task[bytes] | None = None
        self._active_write: asyncio.Task[None] | None = None
        self._failed = False
        self._cleanup_task: asyncio.Task[None] | None = None
        self._cleanup_done = asyncio.Event()

    async def read_line(self, *, max_bytes: int) -> bytes:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        async with self._read_lock:
            self._ensure_open()
            while True:
                newline = self._buffer.find(b"\n")
                if newline >= 0:
                    size = newline + 1
                    if size > max_bytes:
                        self._buffer.clear()
                        self._failed = True
                        raise MessageTooLargeError(
                            f"transport line exceeds the {max_bytes}-byte limit"
                        )
                    line = bytes(self._buffer[:size])
                    del self._buffer[:size]
                    return line
                if len(self._buffer) >= max_bytes:
                    self._buffer.clear()
                    self._failed = True
                    raise MessageTooLargeError(f"transport line exceeds the {max_bytes}-byte limit")
                task = asyncio.create_task(
                    self._reader.read(min(_READ_CHUNK_BYTES, max_bytes - len(self._buffer)))
                )
                self._active_read = task
                read_failed = False
                try:
                    chunk = await task
                except asyncio.CancelledError:
                    raise
                except Exception:
                    read_failed = True
                    chunk = b""
                finally:
                    self._active_read = None
                if read_failed:
                    self._buffer.clear()
                    self._failed = True
                    raise TransportClosedError("transport read failed")
                if not chunk:
                    self._buffer.clear()
                    self._failed = True
                    raise TransportClosedError("transport reached EOF")
                self._buffer.extend(chunk)

    async def write_line(self, data: bytes) -> None:
        _validate_write_line(data)
        async with self._write_lock:
            self._ensure_open()
            write_failed = False
            try:
                self._writer.write(data)
                task = asyncio.create_task(self._writer.drain())
                self._active_write = task
                try:
                    await task
                finally:
                    self._active_write = None
            except asyncio.CancelledError:
                self._failed = True
                raise
            except Exception:
                write_failed = True
            if write_failed:
                self._failed = True
                raise TransportClosedError("transport write failed")

    async def close(self) -> None:
        async with self._close_lock:
            if self._cleanup_task is None:
                self._cleanup_task = asyncio.create_task(self._run_cleanup())
                self._cleanup_task.add_done_callback(self._finish_cleanup)
            cleanup_task = self._cleanup_task
        await self._cleanup_done.wait()
        cleanup_task.result()

    def _finish_cleanup(self, task: asyncio.Task[None]) -> None:
        _consume_task_exception(task)
        self._cleanup_done.set()

    async def _run_cleanup(self) -> None:
        self._buffer.clear()
        active = [task for task in (self._active_read, self._active_write) if task is not None]
        for task in active:
            task.cancel()
        for task in active:
            with suppress(asyncio.CancelledError, Exception):
                await task
        cleanup_failed = False
        try:
            self._writer.close()
        except Exception:
            cleanup_failed = True
        try:
            await asyncio.wait_for(self._writer.wait_closed(), _STREAM_CLOSE_SECONDS)
        except (AttributeError, NotImplementedError):
            pass
        except Exception:
            cleanup_failed = True
        if not await self._close_owned_resource():
            cleanup_failed = True
        if cleanup_failed:
            raise TransportCleanupError("transport cleanup could not prove resource closure")

    async def _close_owned_resource(self) -> bool:
        return True

    def _ensure_open(self) -> None:
        if self._cleanup_task is not None or self._failed:
            raise TransportClosedError("transport is closed")


class _ProcessByteChannel(_StreamByteChannel):
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: Any,
        process: asyncio.subprocess.Process,
        *,
        owns_process_group: bool = False,
    ) -> None:
        super().__init__(reader, writer)
        self._process = process
        self._process_owner = _OwnedProcess(process, owns_process_group=owns_process_group)

    async def _close_owned_resource(self) -> bool:
        return await self._process_owner.close()


class _OwnedProcess:
    """Bounded direct-process and POSIX process-group cleanup owner."""

    def __init__(
        self,
        process: asyncio.subprocess.Process,
        *,
        owns_process_group: bool,
    ) -> None:
        self._process = process
        self._owns_process_group = owns_process_group
        self._wait_task = asyncio.create_task(process.wait())
        self._wait_task.add_done_callback(_consume_task_exception)

    async def close(self) -> bool:
        if await self._wait_for_exit(_PROCESS_EOF_GRACE_SECONDS):
            return True
        self._signal(_SIGNAL_TERMINATE)
        if await self._wait_for_exit(_PROCESS_TERMINATE_SECONDS):
            return True
        self._signal(_SIGNAL_KILL)
        return await self._wait_for_exit(_PROCESS_KILL_SECONDS)

    def _signal(self, signal_number: int) -> None:
        try:
            if self._owns_process_group:
                os.killpg(self._process.pid, signal_number)
            elif signal_number == _SIGNAL_TERMINATE:
                self._process.terminate()
            else:
                self._process.kill()
        except Exception:
            pass

    async def _wait_for_exit(self, timeout: float) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        try:
            await asyncio.wait_for(asyncio.shield(self._wait_task), timeout)
        except TimeoutError:
            return False
        except Exception:
            return False
        if self._process.returncode is None:
            return False
        while self._owns_process_group and self._process_group_alive():
            remaining = deadline - loop.time()
            if remaining <= 0:
                return False
            await asyncio.sleep(min(0.01, remaining))
        return True

    def _process_group_alive(self) -> bool:
        try:
            os.killpg(self._process.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True


class _InjectedByteChannel:
    """Conformance and ownership guard around a caller-supplied channel."""

    def __init__(self, channel: ByteChannel, ownership: TransportOwnership) -> None:
        self._channel = channel
        self._ownership = ownership
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._close_lock = asyncio.Lock()
        self._active_read: asyncio.Task[bytes] | None = None
        self._active_write: asyncio.Task[None] | None = None
        self._failed = False
        self._cleanup_task: asyncio.Task[None] | None = None
        self._cleanup_done = asyncio.Event()

    async def read_line(self, *, max_bytes: int) -> bytes:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        async with self._read_lock:
            self._ensure_open()
            task = asyncio.create_task(self._channel.read_line(max_bytes=max_bytes))
            self._active_read = task
            read_failed = False
            try:
                line = await task
            except asyncio.CancelledError:
                raise
            except Exception:
                read_failed = True
                line = b""
            finally:
                self._active_read = None
            if read_failed:
                self._failed = True
                raise TransportClosedError("injected transport read failed")
            if not isinstance(line, bytes):
                self._failed = True
                raise JsonRpcFramingError("injected transport returned a non-bytes line")
            if len(line) > max_bytes:
                self._failed = True
                raise MessageTooLargeError(
                    f"injected transport line exceeds the {max_bytes}-byte limit"
                )
            if not line.endswith(b"\n") or b"\n" in line[:-1]:
                self._failed = True
                raise JsonRpcFramingError(
                    "injected transport returned an invalid newline-delimited record"
                )
            return line

    async def write_line(self, data: bytes) -> None:
        _validate_write_line(data)
        async with self._write_lock:
            self._ensure_open()
            task = asyncio.create_task(self._channel.write_line(data))
            self._active_write = task
            write_failed = False
            try:
                await task
            except asyncio.CancelledError:
                self._failed = True
                task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await task
                raise
            except Exception:
                write_failed = True
            finally:
                self._active_write = None
            if write_failed:
                self._failed = True
                raise TransportClosedError("injected transport write failed")

    async def close(self) -> None:
        async with self._close_lock:
            if self._cleanup_task is None:
                self._cleanup_task = asyncio.create_task(self._run_cleanup())
                self._cleanup_task.add_done_callback(self._finish_cleanup)
            cleanup_task = self._cleanup_task
        await self._cleanup_done.wait()
        cleanup_task.result()

    def _finish_cleanup(self, task: asyncio.Task[None]) -> None:
        _consume_task_exception(task)
        self._cleanup_done.set()

    async def _run_cleanup(self) -> None:
        active = [task for task in (self._active_read, self._active_write) if task is not None]
        for task in active:
            task.cancel()
        for task in active:
            with suppress(asyncio.CancelledError, Exception):
                await task
        if self._ownership is TransportOwnership.BORROWED:
            return
        close_failed = False
        try:
            await asyncio.wait_for(self._channel.close(), _STREAM_CLOSE_SECONDS)
        except Exception:
            close_failed = True
        if close_failed:
            raise TransportCleanupError("owned injected transport cleanup failed")

    def _ensure_open(self) -> None:
        if self._cleanup_task is not None or self._failed:
            raise TransportClosedError("injected transport is closed")


class _SingleUseTransport:
    capability: TransportCapability

    def __init__(self) -> None:
        self._claimed = False

    def _claim(self) -> None:
        if self._claimed:
            raise TransportOwnershipError("transport already has a connection owner")
        self._claimed = True


class StdioTransport(_SingleUseTransport):
    """Own one exact Codex app-server process using JSON lines on stdio."""

    capability = TransportCapability.OWNED_STDIO

    def __init__(self, binary: BinaryIdentity) -> None:
        if not isinstance(binary, BinaryIdentity):
            raise TypeError("binary must be BinaryIdentity")
        super().__init__()
        self._binary = binary

    async def _open_channel(self) -> ByteChannel:
        self._claim()
        if not _verify_binary(self._binary):
            raise TransportStartError("owned stdio binary identity is not current")
        spawn_failed = False
        kwargs: dict[str, object] = {
            "stdin": asyncio.subprocess.PIPE,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.DEVNULL,
            "limit": _STREAM_BUFFER_LIMIT,
        }
        if os.name == "posix":
            kwargs["start_new_session"] = True
        try:
            process = await asyncio.create_subprocess_exec(
                str(self._binary.path),
                "app-server",
                "--listen",
                "stdio://",
                **kwargs,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            spawn_failed = True
            process = None
        if spawn_failed or process is None or process.stdin is None or process.stdout is None:
            if process is not None and not await _dispose_incomplete_process(
                process, owns_process_group=os.name == "posix"
            ):
                raise TransportCleanupError("incomplete stdio process cleanup failed")
            raise TransportStartError("owned stdio process could not start")
        channel = _ProcessByteChannel(
            process.stdout,
            process.stdin,
            process,
            owns_process_group=os.name == "posix",
        )
        if not _verify_binary(self._binary):
            await channel.close()
            raise TransportStartError("owned stdio binary changed during start")
        return channel


class UnixSocketTransport(_SingleUseTransport):
    """Own one client connection to an explicitly addressed local Unix socket."""

    capability = TransportCapability.UNIX_SOCKET

    def __init__(self, socket_path: os.PathLike[str] | str) -> None:
        super().__init__()
        invalid_type = False
        try:
            raw = os.fspath(socket_path)
        except TypeError:
            invalid_type = True
            raw = ""
        if invalid_type or not isinstance(raw, str):
            raise TypeError("socket_path must be a string path")
        path = Path(raw)
        encoded = os.fsencode(raw)
        if (
            not path.is_absolute()
            or "\x00" in raw
            or ".." in path.parts
            or len(encoded) > _PORTABLE_UNIX_PATH_BYTES
        ):
            raise ValueError("socket_path must be a safe absolute portable Unix-socket path")
        self._socket_path = path

    async def _open_channel(self) -> ByteChannel:
        self._claim()
        connect_failed = False
        try:
            reader, writer = await asyncio.open_unix_connection(
                path=str(self._socket_path), limit=_STREAM_BUFFER_LIMIT
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            connect_failed = True
            reader = writer = None
        if connect_failed or reader is None or writer is None:
            raise TransportStartError("Unix-socket connection could not start")
        return _StreamByteChannel(reader, writer)


class InjectedTransport(_SingleUseTransport):
    """Compose an explicit caller-supplied channel without hidden I/O creation."""

    capability = TransportCapability.INJECTED_BYTE_CHANNEL

    def __init__(
        self,
        channel: ByteChannel,
        *,
        ownership: TransportOwnership,
    ) -> None:
        if not isinstance(ownership, TransportOwnership):
            raise TypeError("ownership must be TransportOwnership")
        for method in ("read_line", "write_line", "close"):
            if not callable(getattr(channel, method, None)):
                raise TypeError("channel must implement ByteChannel")
        super().__init__()
        self._channel = channel
        self._ownership = ownership

    async def _open_channel(self) -> ByteChannel:
        self._claim()
        return _InjectedByteChannel(self._channel, self._ownership)


def _verify_binary(binary: BinaryIdentity) -> bool:
    path = binary.path
    if binary.reported_version != PINNED_PROTOCOL.codex_version or not path.is_absolute():
        return False
    try:
        if path.resolve(strict=True) != path or not path.is_file() or not os.access(path, os.X_OK):
            return False
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
    except OSError:
        return False
    identity_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in identity_fields):
        return False
    return hashlib.sha256(data).hexdigest() == binary.sha256


async def _dispose_incomplete_process(
    process: asyncio.subprocess.Process,
    *,
    owns_process_group: bool,
) -> bool:
    if process.stdin is not None:
        with suppress(Exception):
            process.stdin.close()
    return await _OwnedProcess(process, owns_process_group=owns_process_group).close()
