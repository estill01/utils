"""Transport-independent, bounded JSON-RPC request state."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Protocol

from .compatibility import (
    PINNED_PROTOCOL,
    CompatibilityResult,
    _load_json,
    _packaged_protocol_root,
)
from .errors import (
    CorrelationError,
    JsonRpcFramingError,
    JsonRpcValidationError,
    MessageTooLargeError,
    RemoteRpcError,
    RequestLimitError,
    SchemaRootMismatchError,
    TransportCleanupError,
    UnsupportedFeatureError,
)
from .surface import RequestCapability

_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


class ByteChannel(Protocol):
    """One asynchronous JSON-lines byte channel supplied by a transport."""

    async def read_line(self, *, max_bytes: int) -> bytes:
        """Read one line, including its terminal newline, within ``max_bytes``."""

    async def write_line(self, data: bytes) -> None:
        """Write one complete line, including its terminal newline."""

    async def close(self) -> None:
        """Close the channel and unblock any active read."""


@dataclass(frozen=True, slots=True)
class _RpcLimits:
    """Private RPC bounds later populated from the public client limits."""

    max_message_bytes: int = 8 * 1024 * 1024
    max_pending_calls: int = 256
    max_request_id: int = _INT64_MAX

    def __post_init__(self) -> None:
        if self.max_message_bytes < 2:
            raise ValueError("max_message_bytes must accommodate content and a newline")
        if self.max_pending_calls < 1:
            raise ValueError("max_pending_calls must be positive")
        if not 1 <= self.max_request_id <= _INT64_MAX:
            raise ValueError("max_request_id must be within the positive int64 range")
        if self.max_pending_calls > self.max_request_id:
            raise ValueError("max_pending_calls cannot exceed the request-ID range")


@dataclass(slots=True)
class _PendingCall:
    capability: RequestCapability | None
    future: asyncio.Future[Any]


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key: {key}")
        result[key] = value
    return result


class _EnvelopeValidator:
    """Validate the three RPC envelopes against the retained official schemas."""

    def __init__(self, compatibility: CompatibilityResult) -> None:
        if compatibility.target != PINNED_PROTOCOL:
            raise SchemaRootMismatchError("RPC compatibility target is not the frozen target")
        protocol_root = _packaged_protocol_root()
        metadata = _load_json(
            protocol_root.joinpath("compatibility.json"), "compatibility metadata"
        )
        if compatibility.semantic_schema_root_sha256 != metadata["semantic_schema_root_sha256"]:
            raise SchemaRootMismatchError("RPC compatibility result has the wrong semantic root")
        schema_root = protocol_root.joinpath("upstream", PINNED_PROTOCOL.codex_version)
        self._request = _load_json(schema_root.joinpath("JSONRPCRequest.json"), "JSONRPCRequest")
        self._notification = _load_json(
            schema_root.joinpath("JSONRPCNotification.json"), "JSONRPCNotification"
        )
        self._response = _load_json(schema_root.joinpath("JSONRPCResponse.json"), "JSONRPCResponse")
        self._error = _load_json(schema_root.joinpath("JSONRPCError.json"), "JSONRPCError")

    def request(self, value: object, *, request_id: int) -> None:
        self._validate(value, self._request, self._request, "request")
        if not isinstance(value, Mapping) or value.get("id") != request_id:
            raise JsonRpcValidationError("outbound request ID changed during validation")
        self._integer_id(value["id"], "request.id")

    def response(self, value: object) -> tuple[int, bool]:
        if not isinstance(value, Mapping):
            raise JsonRpcValidationError("inbound JSON-RPC message must be an object")
        has_result = "result" in value
        has_error = "error" in value
        if has_result == has_error:
            raise JsonRpcValidationError(
                "inbound JSON-RPC response must contain exactly one of result or error"
            )
        schema = self._error if has_error else self._response
        self._validate(value, schema, schema, "response")
        request_id = self._integer_id(value["id"], "response.id")
        return request_id, has_error

    def initialized_notification(self, value: object) -> None:
        self._validate(value, self._notification, self._notification, "notification")
        if value != {"method": "initialized"}:
            raise JsonRpcValidationError("initialized notification changed during validation")

    @staticmethod
    def _integer_id(value: object, path: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise JsonRpcValidationError(f"{path} must be an integer")
        if not 1 <= value <= _INT64_MAX:
            raise JsonRpcValidationError(f"{path} must be a positive int64")
        return value

    def _validate(
        self,
        value: object,
        schema: object,
        root: Mapping[str, Any],
        path: str,
    ) -> None:
        if schema is True:
            return
        if schema is False or not isinstance(schema, Mapping):
            raise JsonRpcValidationError(f"{path} has an invalid retained schema")
        reference = schema.get("$ref")
        if reference is not None:
            if not isinstance(reference, str) or not reference.startswith("#/definitions/"):
                raise JsonRpcValidationError(f"{path} uses an unsupported schema reference")
            name = reference.removeprefix("#/definitions/")
            definitions = root.get("definitions")
            if not isinstance(definitions, Mapping) or name not in definitions:
                raise JsonRpcValidationError(f"{path} references a missing schema definition")
            self._validate(value, definitions[name], root, path)
            return
        variants = schema.get("anyOf")
        if variants is not None:
            if not isinstance(variants, list):
                raise JsonRpcValidationError(f"{path} has malformed anyOf constraints")
            failures = 0
            for variant in variants:
                try:
                    self._validate(value, variant, root, path)
                except JsonRpcValidationError:
                    failures += 1
                else:
                    return
            raise JsonRpcValidationError(
                f"{path} does not satisfy any retained schema variant ({failures} rejected)"
            )
        expected = schema.get("type")
        if isinstance(expected, list):
            if any(self._matches_type(value, item) for item in expected):
                return
            raise JsonRpcValidationError(f"{path} has the wrong JSON type")
        if isinstance(expected, str) and not self._matches_type(value, expected):
            raise JsonRpcValidationError(f"{path} must be {expected}")
        if (
            expected == "integer"
            and schema.get("format") == "int64"
            and not _INT64_MIN <= value <= _INT64_MAX  # type: ignore[operator]
        ):
            raise JsonRpcValidationError(f"{path} is outside int64")
        if expected != "object":
            return
        if not isinstance(value, Mapping):
            raise JsonRpcValidationError(f"{path} must be object")
        required = schema.get("required", [])
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            raise JsonRpcValidationError(f"{path} has malformed required constraints")
        missing = [item for item in required if item not in value]
        if missing:
            raise JsonRpcValidationError(f"{path} is missing required fields: {missing}")
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            raise JsonRpcValidationError(f"{path} has malformed property constraints")
        for key, child_schema in properties.items():
            if key in value:
                self._validate(value[key], child_schema, root, f"{path}.{key}")

    @staticmethod
    def _matches_type(value: object, expected: object) -> bool:
        if expected == "null":
            return value is None
        if expected == "object":
            return isinstance(value, Mapping)
        if expected == "string":
            return isinstance(value, str)
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "array":
            return isinstance(value, list)
        raise JsonRpcValidationError(f"unsupported retained JSON type: {expected!r}")


class _RpcEngine:
    """Private request/response engine shared by later transports and sessions."""

    def __init__(
        self,
        channel: ByteChannel,
        compatibility: CompatibilityResult,
        *,
        limits: _RpcLimits | None = None,
    ) -> None:
        self._channel = channel
        self._compatibility = compatibility
        self._limits = limits or _RpcLimits()
        self._validator = _EnvelopeValidator(compatibility)
        self._pending: dict[int, _PendingCall] = {}
        history_size = max(2, self._limits.max_pending_calls * 2)
        self._settled_order: deque[int] = deque(maxlen=history_size)
        self._settled: set[int] = set()
        self._abandoned_order: deque[int] = deque(maxlen=history_size)
        self._abandoned: set[int] = set()
        self._next_request_id = 1
        self._write_lock = asyncio.Lock()
        self._reader_task: asyncio.Task[None] | None = None
        self._closed = asyncio.Event()
        self._failure: BaseException | None = None
        self._channel_closed = False
        self._cleanup_failure: TransportCleanupError | None = None

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def failure(self) -> BaseException | None:
        return self._failure

    async def start(self) -> None:
        if self._failure is not None:
            raise self._failure
        if self._reader_task is None:
            self._reader_task = asyncio.create_task(self._read_responses())

    async def call(
        self,
        capability: RequestCapability,
        params: object,
        *,
        timeout: float | None = None,
    ) -> Any:
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be positive")
        if not isinstance(capability, RequestCapability):
            raise TypeError("capability must be RequestCapability")
        if not self._compatibility.features.supports(capability):
            raise UnsupportedFeatureError(f"request capability is unavailable: {capability.value}")
        return await self._call_method(
            capability.value,
            params,
            capability=capability,
            timeout=timeout,
        )

    async def _initialize(self, params: object) -> Any:
        return await self._call_method("initialize", params, capability=None, timeout=None)

    async def _send_initialized(self) -> None:
        if self._failure is not None:
            raise self._failure
        notification = {"method": "initialized"}
        self._validator.initialized_notification(notification)
        line = self._encode_value(notification, "initialized notification")
        write_failed = False
        try:
            async with self._write_lock:
                await self._channel.write_line(line)
        except asyncio.CancelledError:
            raise
        except Exception:
            write_failed = True
        if write_failed:
            failure = JsonRpcFramingError("byte-channel write failed for initialized notification")
            await self._fail(failure)
            raise failure

    async def _call_method(
        self,
        method: str,
        params: object,
        *,
        capability: RequestCapability | None,
        timeout: float | None,
    ) -> Any:
        await self.start()
        request_id, future = self._register(capability)
        request = {"id": request_id, "method": method, "params": params}
        write_failed = False
        try:
            line = self._encode_request(request, request_id=request_id)
            async with self._write_lock:
                await self._channel.write_line(line)
        except asyncio.CancelledError:
            self._abandon(request_id, future)
            raise
        except (JsonRpcValidationError, MessageTooLargeError):
            self._discard_unsent(request_id, future)
            raise
        except Exception:
            write_failed = True
        if write_failed:
            self._discard_unsent(request_id, future)
            failure = JsonRpcFramingError(f"byte-channel write failed for request {request_id}")
            await self._fail(failure)
            raise failure
        try:
            if timeout is None:
                return await asyncio.shield(future)
            return await asyncio.wait_for(asyncio.shield(future), timeout)
        except TimeoutError:
            self._abandon(request_id, future)
            raise
        except asyncio.CancelledError:
            self._abandon(request_id, future)
            raise

    async def wait_closed(self) -> None:
        await self._closed.wait()

    async def close(self) -> None:
        if self._failure is None:
            await self._fail(JsonRpcFramingError("RPC engine closed"))
        else:
            await self._close_channel()
        reader = self._reader_task
        if reader is not None and reader is not asyncio.current_task() and not reader.done():
            reader.cancel()
            with suppress(asyncio.CancelledError):
                await reader
        self._closed.set()
        if self._cleanup_failure is not None:
            raise self._cleanup_failure

    def _register(self, capability: RequestCapability | None) -> tuple[int, asyncio.Future[Any]]:
        if self._failure is not None:
            raise self._failure
        if len(self._pending) >= self._limits.max_pending_calls:
            raise RequestLimitError(
                f"pending request limit reached: {self._limits.max_pending_calls}"
            )
        request_id = self._allocate_id()
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = _PendingCall(capability=capability, future=future)
        return request_id, future

    def _allocate_id(self) -> int:
        for _ in range(self._limits.max_pending_calls + 1):
            request_id = self._next_request_id
            self._next_request_id = (
                1 if request_id == self._limits.max_request_id else request_id + 1
            )
            if (
                request_id not in self._pending
                and request_id not in self._settled
                and request_id not in self._abandoned
            ):
                return request_id
        raise RequestLimitError("no request ID is safely reusable")

    def _encode_request(self, request: dict[str, object], *, request_id: int) -> bytes:
        self._validator.request(request, request_id=request_id)
        return self._encode_value(request, f"request {request_id}")

    def _encode_value(self, value: object, label: str) -> bytes:
        try:
            payload = json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError):
            payload = None
        if payload is None:
            raise JsonRpcValidationError(f"{label} contains a non-JSON value")
        line = payload + b"\n"
        if len(line) > self._limits.max_message_bytes:
            raise MessageTooLargeError(
                f"{label} is {len(line)} bytes; limit is {self._limits.max_message_bytes}"
            )
        return line

    async def _read_responses(self) -> None:
        try:
            while self._failure is None:
                try:
                    line = await self._channel.read_line(max_bytes=self._limits.max_message_bytes)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    await self._fail(JsonRpcFramingError("byte-channel read failed"))
                    return
                self._accept_response(line)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            failure = (
                error
                if isinstance(error, _APP_RPC_ERRORS)
                else JsonRpcFramingError("byte-channel read failed")
            )
            await self._fail(failure)
        finally:
            self._closed.set()

    def _accept_response(self, line: bytes) -> None:
        value = self._decode_line(line)
        request_id, is_error = self._validator.response(value)
        if request_id in self._abandoned:
            self._remove_history(self._abandoned_order, self._abandoned, request_id)
            return
        pending = self._pending.pop(request_id, None)
        if pending is None:
            kind = "duplicate" if request_id in self._settled else "unmatched"
            raise CorrelationError(f"{kind} response ID: {request_id}")
        self._remember(self._settled_order, self._settled, request_id)
        if is_error:
            remote = value["error"]
            pending.future.set_exception(
                RemoteRpcError(
                    request_id=request_id,
                    code=remote["code"],
                    has_data="data" in remote,
                )
            )
        else:
            pending.future.set_result(value["result"])

    def _decode_line(self, line: bytes) -> object:
        if not isinstance(line, bytes):
            raise JsonRpcFramingError("byte channel returned a non-bytes line")
        if len(line) > self._limits.max_message_bytes:
            raise MessageTooLargeError(
                f"inbound line is {len(line)} bytes; limit is {self._limits.max_message_bytes}"
            )
        if not line.endswith(b"\n"):
            raise JsonRpcFramingError("inbound line has no terminal newline")
        payload = line[:-1]
        if b"\n" in payload:
            raise JsonRpcFramingError("inbound record contains more than one line")
        if payload.endswith(b"\r"):
            payload = payload[:-1]
        if not payload:
            raise JsonRpcFramingError("inbound line is empty")
        try:
            return json.loads(
                payload,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            value = None
        if value is None:
            raise JsonRpcFramingError("inbound line is not strict JSON")
        return value

    def _discard_unsent(self, request_id: int, future: asyncio.Future[Any]) -> None:
        pending = self._pending.get(request_id)
        if pending is not None and pending.future is future:
            del self._pending[request_id]
            future.cancel()
        elif future.done() and not future.cancelled():
            future.exception()

    def _abandon(self, request_id: int, future: asyncio.Future[Any]) -> None:
        pending = self._pending.get(request_id)
        if pending is not None and pending.future is future:
            del self._pending[request_id]
            future.cancel()
            self._remember(self._abandoned_order, self._abandoned, request_id)
        elif future.done() and not future.cancelled():
            future.exception()

    @staticmethod
    def _remember(order: deque[int], members: set[int], request_id: int) -> None:
        if order.maxlen is not None and len(order) == order.maxlen:
            members.discard(order[0])
        order.append(request_id)
        members.add(request_id)

    @staticmethod
    def _remove_history(order: deque[int], members: set[int], request_id: int) -> None:
        members.remove(request_id)
        order.remove(request_id)

    async def _fail(self, failure: BaseException) -> None:
        if self._failure is None:
            self._failure = failure
            pending, self._pending = self._pending, {}
            for call in pending.values():
                if not call.future.done():
                    call.future.set_exception(failure)
        await self._close_channel()
        self._closed.set()

    async def _close_channel(self) -> None:
        if self._channel_closed:
            return
        self._channel_closed = True
        try:
            await self._channel.close()
        except TransportCleanupError as error:
            self._cleanup_failure = error
        except Exception:
            self._cleanup_failure = TransportCleanupError("byte-channel cleanup failed")


_APP_RPC_ERRORS = (
    CorrelationError,
    JsonRpcFramingError,
    JsonRpcValidationError,
    MessageTooLargeError,
)
