"""One initialized typed app-server session over the private RPC engine."""

from __future__ import annotations

import asyncio
import math
from contextlib import suppress
from dataclasses import dataclass
from typing import TypeVar

from .compatibility import (
    PINNED_PROTOCOL,
    CompatibilityResult,
    _load_json,
    _packaged_protocol_root,
)
from .errors import (
    InitializationError,
    JsonRpcValidationError,
    SessionStateError,
    TransportCleanupError,
    UnsupportedFeatureError,
)
from .models import (
    ClientIdentity,
    ReviewStartParams,
    ReviewStartResponse,
    ThreadListParams,
    ThreadListResponse,
    ThreadReadParams,
    ThreadReadResponse,
    ThreadResumeParams,
    ThreadResumeResponse,
    ThreadStartParams,
    ThreadStartResponse,
    TurnInterruptParams,
    TurnInterruptResponse,
    TurnStartParams,
    TurnStartResponse,
    TurnSteerParams,
    TurnSteerResponse,
    _decode_document,
)
from .rpc import _EnvelopeValidator, _RpcEngine, _RpcLimits
from .surface import FeatureSet, NotificationCapability, RequestCapability, TransportCapability
from .transport import ClientTransport

_ModelT = TypeVar("_ModelT")


@dataclass(frozen=True, slots=True)
class ClientLimits:
    """Frozen public bounds for one client owner."""

    max_message_bytes: int = 8 * 1024 * 1024
    max_pending_calls: int = 256
    max_events: int = 1024
    max_callbacks: int = 64
    max_backoff_seconds: float = 30.0

    def __post_init__(self) -> None:
        for name in ("max_message_bytes", "max_pending_calls", "max_events", "max_callbacks"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_message_bytes < 2:
            raise ValueError("max_message_bytes must accommodate content and a newline")
        if (
            isinstance(self.max_backoff_seconds, bool)
            or not isinstance(self.max_backoff_seconds, (int, float))
            or not math.isfinite(self.max_backoff_seconds)
            or self.max_backoff_seconds <= 0
        ):
            raise ValueError("max_backoff_seconds must be positive and finite")


def _retained_notification_methods() -> tuple[str, ...]:
    root = _packaged_protocol_root().joinpath("upstream", PINNED_PROTOCOL.codex_version)
    schema = _load_json(root.joinpath("ServerNotification.json"), "ServerNotification")
    variants = schema.get("oneOf")
    if not isinstance(variants, list):
        raise InitializationError("server notification schema has no closed method union")
    methods: list[str] = []
    for variant in variants:
        if not isinstance(variant, dict):
            raise InitializationError("server notification schema has a malformed variant")
        properties = variant.get("properties")
        method = properties.get("method") if isinstance(properties, dict) else None
        values = method.get("enum") if isinstance(method, dict) else None
        if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], str):
            raise InitializationError("server notification schema has a malformed method")
        methods.append(values[0])
    if len(methods) != len(set(methods)):
        raise InitializationError("server notification schema repeats a method")
    selected = {capability.value for capability in NotificationCapability}
    if not selected.issubset(methods):
        raise InitializationError("selected notification is absent from the retained schema")
    return tuple(sorted(methods))


_BLOCK6_NOTIFICATION_OPTOUTS = _retained_notification_methods()


def _consume_task_exception(task: asyncio.Task[None]) -> None:
    if not task.cancelled():
        with suppress(Exception):
            task.exception()


_DEFAULT_CLIENT_LIMITS = ClientLimits()


class AppServerClient:
    """The single connection owner before and after one initialization handshake."""

    _CONSTRUCTION_TOKEN = object()

    def __init__(
        self,
        token: object,
        transport: ClientTransport,
        compatibility: CompatibilityResult,
        limits: ClientLimits,
        engine: _RpcEngine,
    ) -> None:
        if token is not self._CONSTRUCTION_TOKEN:
            raise TypeError("use AppServerClient.connect")
        self._transport = transport
        self._compatibility = compatibility
        self._limits = limits
        self._engine = engine
        self._state = "connected"
        self._state_lock = asyncio.Lock()
        self._close_lock = asyncio.Lock()
        self._close_task: asyncio.Task[None] | None = None
        self._close_done = asyncio.Event()
        self._session: AppServerSession | None = None

    @classmethod
    async def connect(
        cls,
        transport: ClientTransport,
        compatibility: CompatibilityResult,
        *,
        limits: ClientLimits = _DEFAULT_CLIENT_LIMITS,
    ) -> AppServerClient:
        if not isinstance(compatibility, CompatibilityResult):
            raise TypeError("compatibility must be CompatibilityResult")
        if not isinstance(limits, ClientLimits):
            raise TypeError("limits must be ClientLimits")
        capability = getattr(transport, "capability", None)
        if not isinstance(capability, TransportCapability) or not callable(
            getattr(transport, "_open_channel", None)
        ):
            raise TypeError("transport must implement ClientTransport")
        _EnvelopeValidator(compatibility)
        if not compatibility.features.supports(capability):
            raise UnsupportedFeatureError(
                f"transport capability is unavailable: {capability.value}"
            )
        channel = await transport._open_channel()
        try:
            engine = _RpcEngine(
                channel,
                compatibility,
                limits=_RpcLimits(
                    max_message_bytes=limits.max_message_bytes,
                    max_pending_calls=limits.max_pending_calls,
                ),
            )
        except Exception:
            try:
                await channel.close()
            except Exception:
                raise TransportCleanupError(
                    "failed connection construction did not close"
                ) from None
            raise
        return cls(cls._CONSTRUCTION_TOKEN, transport, compatibility, limits, engine)

    async def initialize(self, identity: ClientIdentity) -> AppServerSession:
        if not isinstance(identity, ClientIdentity):
            raise TypeError("identity must be ClientIdentity")
        async with self._state_lock:
            if self._state != "connected":
                raise SessionStateError("client initialization is available exactly once")
            self._state = "initializing"
            initialization_failed = False
            try:
                params = _decode_document(
                    "v1/InitializeParams.json",
                    {
                        "clientInfo": identity.to_dict(),
                        "capabilities": {
                            "experimentalApi": False,
                            "extensions": {},
                            "mcpServerOpenaiFormElicitation": False,
                            "optOutNotificationMethods": list(_BLOCK6_NOTIFICATION_OPTOUTS),
                            "requestAttestation": False,
                        },
                    },
                )
                result = await self._engine._initialize(params.to_dict())
                _decode_document("v1/InitializeResponse.json", result)
                await self._engine._send_initialized()
            except asyncio.CancelledError:
                self._state = "failed"
                await self._close_after_failed_initialization()
                raise
            except Exception:
                initialization_failed = True
            if initialization_failed:
                self._state = "failed"
                await self._close_after_failed_initialization()
                raise InitializationError("app-server initialization failed")
            capabilities = FeatureSet(
                requests=self._compatibility.features.requests,
                notifications=frozenset(),
                callbacks=frozenset(),
                transports=frozenset({self._transport.capability}),
            )
            self._session = AppServerSession(
                AppServerSession._CONSTRUCTION_TOKEN, self, capabilities
            )
            self._state = "initialized"
            return self._session

    async def _close_after_failed_initialization(self) -> None:
        with suppress(TransportCleanupError):
            await self._engine.close()

    async def close(self) -> None:
        async with self._close_lock:
            if self._close_task is None:
                self._close_task = asyncio.create_task(self._run_close())
                self._close_task.add_done_callback(self._finish_close)
            close_task = self._close_task
        await self._close_done.wait()
        close_task.result()

    def _finish_close(self, task: asyncio.Task[None]) -> None:
        _consume_task_exception(task)
        self._close_done.set()

    async def _run_close(self) -> None:
        async with self._state_lock:
            self._state = "closed"
            await self._engine.close()

    async def _invalidate(self, failure: JsonRpcValidationError) -> None:
        self._state = "failed"
        await self._engine._fail(failure)


class AppServerSession:
    """One initialized generation exposing only the eight frozen typed operations."""

    _CONSTRUCTION_TOKEN = object()

    def __init__(
        self,
        token: object,
        client: AppServerClient,
        capabilities: FeatureSet,
    ) -> None:
        if token is not self._CONSTRUCTION_TOKEN:
            raise TypeError("sessions are created only by AppServerClient.initialize")
        self._client = client
        self._capabilities = capabilities
        self._generation = 1

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def capabilities(self) -> FeatureSet:
        return self._capabilities

    def _ensure_active(self) -> None:
        if self._client._engine.failure is not None:
            self._client._state = "failed"
        if self._client._state != "initialized":
            raise SessionStateError("typed operation requires an active initialized session")

    async def close(self) -> None:
        await self._client.close()

    async def start_thread(
        self, params: ThreadStartParams, *, timeout: float | None = None
    ) -> ThreadStartResponse:
        return await self._operation(
            RequestCapability.THREAD_START,
            params,
            ThreadStartParams,
            ThreadStartResponse,
            timeout,
        )

    async def resume_thread(
        self, params: ThreadResumeParams, *, timeout: float | None = None
    ) -> ThreadResumeResponse:
        return await self._operation(
            RequestCapability.THREAD_RESUME,
            params,
            ThreadResumeParams,
            ThreadResumeResponse,
            timeout,
        )

    async def read_thread(
        self, params: ThreadReadParams, *, timeout: float | None = None
    ) -> ThreadReadResponse:
        return await self._operation(
            RequestCapability.THREAD_READ,
            params,
            ThreadReadParams,
            ThreadReadResponse,
            timeout,
        )

    async def list_threads(
        self, params: ThreadListParams, *, timeout: float | None = None
    ) -> ThreadListResponse:
        return await self._operation(
            RequestCapability.THREAD_LIST,
            params,
            ThreadListParams,
            ThreadListResponse,
            timeout,
        )

    async def start_turn(
        self, params: TurnStartParams, *, timeout: float | None = None
    ) -> TurnStartResponse:
        return await self._operation(
            RequestCapability.TURN_START,
            params,
            TurnStartParams,
            TurnStartResponse,
            timeout,
        )

    async def steer_turn(
        self, params: TurnSteerParams, *, timeout: float | None = None
    ) -> TurnSteerResponse:
        return await self._operation(
            RequestCapability.TURN_STEER,
            params,
            TurnSteerParams,
            TurnSteerResponse,
            timeout,
        )

    async def interrupt_turn(
        self, params: TurnInterruptParams, *, timeout: float | None = None
    ) -> TurnInterruptResponse:
        return await self._operation(
            RequestCapability.TURN_INTERRUPT,
            params,
            TurnInterruptParams,
            TurnInterruptResponse,
            timeout,
        )

    async def start_review(
        self, params: ReviewStartParams, *, timeout: float | None = None
    ) -> ReviewStartResponse:
        return await self._operation(
            RequestCapability.REVIEW_START,
            params,
            ReviewStartParams,
            ReviewStartResponse,
            timeout,
        )

    async def _operation(
        self,
        capability: RequestCapability,
        params: object,
        expected_params: type[object],
        response_type: type[_ModelT],
        timeout: float | None,
    ) -> _ModelT:
        self._ensure_active()
        if not isinstance(params, expected_params):
            raise TypeError(f"{capability.value} requires its exact frozen params model")
        if not self._capabilities.supports(capability):
            raise UnsupportedFeatureError(f"request capability is unavailable: {capability.value}")
        try:
            result = await self._client._engine.call(
                capability,
                params.to_dict(),  # type: ignore[attr-defined]
                timeout=timeout,
            )
        except Exception:
            if self._client._engine.failure is not None:
                await self._client._engine.wait_closed()
                self._client._state = "failed"
            raise
        response: _ModelT | None = None
        invalid_result = False
        try:
            response = response_type.from_dict(result)  # type: ignore[attr-defined, no-any-assignment]
        except Exception:
            invalid_result = True
        if invalid_result or response is None:
            failure = JsonRpcValidationError(
                f"{capability.value} result does not match its retained schema"
            )
            await self._client._invalidate(failure)
            raise failure
        return response
