"""Bounded RFC 6455 text frames over a caller-selected local Unix socket.

Owns only the client connection. It never starts, stops or configures a daemon.
No public-network URL, compression extension or binary-message API is exposed.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import struct

from .errors import (
    JsonRpcFramingError,
    MessageTooLargeError,
    TransportClosedError,
    TransportStartError,
)
from .surface import TransportCapability
from .transport import UnixSocketTransport, _StreamByteChannel, _validate_write_line

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_MAX_MESSAGE = 8 * 1024 * 1024
_MAX_FRAMES = 1024


class _WebSocketByteChannel(_StreamByteChannel):
    async def upgrade(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
            "Connection: Upgrade\r\nSec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Key: {key}\r\n\r\n"
        ).encode("ascii")
        self._writer.write(request)
        await self._writer.drain()
        # The reader's 16 KiB limit bounds headers before parsing or allocation.
        raw = await self._reader.readuntil(b"\r\n\r\n")
        if len(raw) > 16384:
            raise TransportStartError("WebSocket upgrade headers exceed the bound")
        try:
            lines = raw.decode("ascii").split("\r\n")
            if lines[0].split()[:2] != ["HTTP/1.1", "101"]:
                raise ValueError("upgrade status")
            headers = {}
            for line in lines[1:]:
                if not line:
                    continue
                name, value = line.split(":", 1)
                name = name.strip().lower()
                if name in headers:
                    raise ValueError("duplicate upgrade header")
                headers[name] = value.strip()
            expected = base64.b64encode(
                hashlib.sha1((key + _GUID).encode(), usedforsecurity=False).digest()
            ).decode()
            if (
                headers.get("upgrade", "").lower() != "websocket"
                or "upgrade"
                not in {x.strip().lower() for x in headers.get("connection", "").split(",")}
                or headers.get("sec-websocket-accept") != expected
                or "sec-websocket-extensions" in headers
                or "sec-websocket-protocol" in headers
            ):
                raise ValueError("upgrade headers")
        except (UnicodeError, ValueError) as error:
            raise TransportStartError("Invalid local WebSocket upgrade") from error

    async def _exact(self, count: int) -> bytes:
        task = asyncio.create_task(self._reader.readexactly(count))
        self._active_read = task
        try:
            return await task
        except asyncio.IncompleteReadError as error:
            raise TransportClosedError("Local WebSocket reached EOF") from error
        finally:
            self._active_read = None

    async def _send(self, opcode: int, payload: bytes) -> None:
        async with self._write_lock:
            self._ensure_open()
            length = len(payload)
            header = bytes([0x80 | opcode])
            if length < 126:
                header += bytes([0x80 | length])
            elif length < 65536:
                header += bytes([0x80 | 126]) + struct.pack("!H", length)
            else:
                header += bytes([0x80 | 127]) + struct.pack("!Q", length)
            mask = os.urandom(4)
            encoded = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            self._writer.write(header + mask + encoded)
            task = asyncio.create_task(self._writer.drain())
            self._active_write = task
            try:
                await task
            except BaseException:
                self._failed = True
                raise
            finally:
                self._active_write = None

    async def write_line(self, data: bytes) -> None:
        _validate_write_line(data)
        if len(data) > _MAX_MESSAGE:
            raise MessageTooLargeError("Local WebSocket message exceeds its bound")
        try:
            data.decode("utf-8")
        except UnicodeError as error:
            raise JsonRpcFramingError("WebSocket text must be UTF-8") from error
        await self._send(1, data[:-1])

    async def read_line(self, *, max_bytes: int) -> bytes:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        bound = min(max_bytes - 1, _MAX_MESSAGE - 1)
        async with self._read_lock:
            self._ensure_open()
            message = bytearray()
            fragmented = False
            try:
                for _ in range(_MAX_FRAMES):
                    first, second = await self._exact(2)
                    final, opcode = bool(first & 0x80), first & 15
                    if first & 0x70 or second & 0x80 or opcode not in {0, 1, 8, 9, 10}:
                        raise JsonRpcFramingError("Unsupported WebSocket frame")
                    length = second & 127
                    if length == 126:
                        length = struct.unpack("!H", await self._exact(2))[0]
                        if length < 126:
                            raise JsonRpcFramingError("Nonminimal WebSocket frame length")
                    elif length == 127:
                        length = struct.unpack("!Q", await self._exact(8))[0]
                        if length < 65536 or length >= 2**63:
                            raise JsonRpcFramingError("Invalid WebSocket frame length")
                    if opcode >= 8:
                        if not final or length > 125 or (opcode == 8 and length == 1):
                            raise JsonRpcFramingError("Invalid WebSocket control frame")
                    elif length + len(message) > bound:
                        raise MessageTooLargeError("Local WebSocket message exceeds its bound")
                    payload = await self._exact(length)
                    if opcode == 8:
                        if len(payload) >= 2:
                            code = struct.unpack("!H", payload[:2])[0]
                            if (
                                code < 1000
                                or code >= 5000
                                or code in {1004, 1005, 1006, 1015}
                                or 1016 <= code < 3000
                            ):
                                raise JsonRpcFramingError("Invalid WebSocket close code")
                            payload[2:].decode("utf-8")
                        raise TransportClosedError("Local WebSocket peer closed")
                    if opcode == 9:
                        await self._send(10, payload)
                        continue
                    if opcode == 10:
                        continue
                    if (opcode == 0) != fragmented:
                        raise JsonRpcFramingError("Invalid WebSocket continuation")
                    message.extend(payload)
                    if final:
                        message.decode("utf-8")
                        return bytes(message) + b"\n"
                    fragmented = True
                raise JsonRpcFramingError("WebSocket frame count exceeds its bound")
            except UnicodeError as error:
                self._failed = True
                raise JsonRpcFramingError("Invalid WebSocket UTF-8") from error
            except BaseException:
                # Partial frames cannot be resumed safely after cancellation.
                self._failed = True
                raise


class LocalWebSocketTransport(UnixSocketTransport):
    """Attach to one explicit local WebSocket control socket, without daemon ownership."""

    capability = TransportCapability.LOCAL_WEBSOCKET

    async def _open_channel(self):
        self._claim()
        channel = None
        try:
            async with asyncio.timeout(5):
                reader, writer = await asyncio.open_unix_connection(
                    str(self._socket_path), limit=16384
                )
                channel = _WebSocketByteChannel(reader, writer)
                await channel.upgrade()
            return channel
        except BaseException as error:
            if channel is not None:
                await asyncio.shield(channel.close())
            if isinstance(error, asyncio.CancelledError):
                raise
            raise TransportStartError("Local WebSocket connection could not start") from error
