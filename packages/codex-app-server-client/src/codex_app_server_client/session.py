"""One initialized typed app-server session over the private RPC engine."""

from __future__ import annotations

import asyncio
import inspect
import math
import sys
import weakref
from collections.abc import AsyncIterator
from contextlib import aclosing, suppress
from dataclasses import dataclass
from typing import TypeVar

from .compatibility import (
    PINNED_PROTOCOL,
    CompatibilityResult,
    _load_json,
    _packaged_protocol_root,
)
from .coordination import ServerCallback, ServerEvent, _AsyncCoordinator
from .errors import (
    AppServerClientError,
    CallCancelledError,
    CallTimeoutError,
    DisconnectedError,
    InitializationError,
    JsonRpcValidationError,
    RestartError,
    SessionStateError,
    StaleGenerationError,
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
from .restart import BackoffHook, RestartContext
from .rpc import _EnvelopeValidator, _RpcEngine, _RpcLimits
from .surface import FeatureSet, NotificationCapability, RequestCapability, TransportCapability
from .transport import (
    ClientTransport,
    InjectedTransport,
    StdioTransport,
    TransportOwnership,
    UnixSocketTransport,
)

_ModelT = TypeVar("_ModelT")
_MAX_CONNECTION_LINEAGES = 256


def _is_finite_number(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)  # type: ignore[arg-type]
    except OverflowError:
        return False


def _consume_current_cancellation() -> None:
    task = asyncio.current_task()
    while task is not None and task.cancelling():
        task.uncancel()


def _current_task_is_cancelling() -> bool:
    task = asyncio.current_task()
    return task is not None and bool(task.cancelling())


@dataclass(frozen=True, slots=True)
class ClientLimits:
    """Frozen public bounds for one client owner."""

    max_message_bytes: int = 8 * 1024 * 1024
    max_pending_calls: int = 256
    max_events: int = 1024
    max_callbacks: int = 64
    max_backoff_seconds: float = 30.0

    def __post_init__(self) -> None:
        for name in (
            "max_message_bytes",
            "max_pending_calls",
            "max_events",
            "max_callbacks",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_message_bytes < 2:
            raise ValueError("max_message_bytes must accommodate content and a newline")
        if self.max_pending_calls > sys.maxsize // 2:
            raise ValueError("max_pending_calls exceeds the safe request-history bound")
        if (
            type(self.max_backoff_seconds) not in (int, float)
            or not _is_finite_number(self.max_backoff_seconds)
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


def _notification_optouts(features: FeatureSet) -> tuple[str, ...]:
    selected_available = {capability.value for capability in features.notifications}
    return tuple(
        method for method in _retained_notification_methods() if method not in selected_available
    )


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
        coordinator: _AsyncCoordinator,
        declared_lineage: object | None,
        channel_lineage: object,
    ) -> None:
        if token is not self._CONSTRUCTION_TOKEN:
            raise TypeError("use AppServerClient.connect")
        self._transport = transport
        self._compatibility = compatibility
        self._limits = limits
        self._engine = engine
        self._coordinator = coordinator
        self._state = "connected"
        self._state_lock = asyncio.Lock()
        self._close_lock = asyncio.Lock()
        self._close_task: asyncio.Task[None] | None = None
        self._close_done = asyncio.Event()
        self._session: AppServerSession | None = None
        self._identity: ClientIdentity | None = None
        self._generation = 1
        self._failure: AppServerClientError | None = None
        self._max_connection_lineages = _MAX_CONNECTION_LINEAGES
        self._connection_lineages: list[weakref.ReferenceType[object]] = []
        self._injected_replacement_safe = type(transport) in (
            StdioTransport,
            UnixSocketTransport,
        ) or (
            type(transport) is InjectedTransport
            and transport._ownership is TransportOwnership.OWNED
        )
        self._remember_connection_lineages(declared_lineage, channel_lineage)

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
        _EnvelopeValidator(compatibility)
        cls._validate_transport(transport, compatibility)
        engine, coordinator, declared_lineage, channel_lineage = await cls._open_connection(
            transport, compatibility, limits, generation=1
        )
        return cls(
            cls._CONSTRUCTION_TOKEN,
            transport,
            compatibility,
            limits,
            engine,
            coordinator,
            declared_lineage,
            channel_lineage,
        )

    @staticmethod
    def _validate_transport(
        transport: ClientTransport, compatibility: CompatibilityResult
    ) -> TransportCapability:
        capability = getattr(transport, "capability", None)
        if not isinstance(capability, TransportCapability) or not callable(
            getattr(transport, "_open_channel", None)
        ):
            raise TypeError("transport must implement ClientTransport")
        if not compatibility.features.supports(capability):
            raise UnsupportedFeatureError(
                f"transport capability is unavailable: {capability.value}"
            )
        return capability

    def _replacement_transport_is_package_owned(self, transport: ClientTransport) -> bool:
        if type(transport) in (StdioTransport, UnixSocketTransport):
            return True
        return (
            self._injected_replacement_safe
            and type(transport) is InjectedTransport
            and transport._ownership is TransportOwnership.OWNED
        )

    @staticmethod
    def _proposed_transport_lineage(transport: ClientTransport) -> object | None:
        failed = False
        try:
            provider = getattr(transport, "_connection_lineage", None)
            if not callable(provider):
                return None
            lineage = provider()
            if inspect.iscoroutine(lineage):
                lineage.close()
                failed = True
                lineage = None
        except asyncio.CancelledError:
            if _current_task_is_cancelling():
                raise
            failed = True
            lineage = None
        except Exception:
            failed = True
            lineage = None
        if failed:
            raise TypeError("transport connection lineage is unavailable")
        if lineage is None:
            raise TypeError("transport connection lineage is unavailable")
        return lineage

    @staticmethod
    def _lineage_reference(
        lineage: object,
    ) -> weakref.ReferenceType[object] | None:
        try:
            return weakref.ref(lineage)
        except TypeError:
            return None

    @staticmethod
    def _unique_lineages(*lineages: object | None) -> list[object]:
        unique: list[object] = []
        for lineage in lineages:
            if lineage is not None and not any(lineage is item for item in unique):
                unique.append(lineage)
        return unique

    def _lineages_are_available(
        self,
        *lineages: object | None,
        required_capacity: int | None = None,
    ) -> bool:
        retained: list[weakref.ReferenceType[object]] = []
        for reference in self._connection_lineages:
            if reference() is not None:
                retained.append(reference)
        self._connection_lineages = retained
        proposed = self._unique_lineages(*lineages)
        if any(self._lineage_reference(lineage) is None for lineage in proposed):
            return False
        if any(
            accepted is lineage
            for reference in retained
            if (accepted := reference()) is not None
            for lineage in proposed
        ):
            return False
        capacity = len(proposed) if required_capacity is None else required_capacity
        return len(retained) + max(len(proposed), capacity) <= self._max_connection_lineages

    def _remember_connection_lineages(self, *lineages: object | None) -> None:
        for lineage in self._unique_lineages(*lineages):
            if any(reference() is lineage for reference in self._connection_lineages):
                continue
            reference = self._lineage_reference(lineage)
            if reference is not None:
                self._connection_lineages.append(reference)

    @classmethod
    async def _open_connection(
        cls,
        transport: ClientTransport,
        compatibility: CompatibilityResult,
        limits: ClientLimits,
        *,
        generation: int,
    ) -> tuple[_RpcEngine, _AsyncCoordinator, object | None, object]:
        proposed_lineage = cls._proposed_transport_lineage(transport)
        try:
            channel = await transport._open_channel()
        except asyncio.CancelledError:
            if _current_task_is_cancelling():
                raise
            raise TransportCleanupError("transport start cleanup is unproven") from None
        try:
            engine = _RpcEngine(
                channel,
                compatibility,
                limits=_RpcLimits(
                    max_message_bytes=limits.max_message_bytes,
                    max_pending_calls=limits.max_pending_calls,
                ),
                generation=generation,
            )
            coordinator = _AsyncCoordinator(
                engine,
                compatibility.features,
                max_events=limits.max_events,
                max_callbacks=limits.max_callbacks,
                generation=generation,
            )
            engine._set_inbound_handler(coordinator)
        except BaseException:
            try:
                await channel.close()
            except Exception:
                raise TransportCleanupError(
                    "failed connection construction did not close"
                ) from None
            raise
        return engine, coordinator, proposed_lineage, channel

    async def initialize(self, identity: ClientIdentity) -> AppServerSession:
        if not isinstance(identity, ClientIdentity):
            raise TypeError("identity must be ClientIdentity")
        async with self._state_lock:
            if self._state != "connected":
                raise SessionStateError("client initialization is available exactly once")
            self._identity = identity
            self._state = "initializing"
            initialization_failed = False
            try:
                await self._initialize_engine(self._engine, identity)
            except asyncio.CancelledError:
                self._state = "failed"
                if _current_task_is_cancelling():
                    self._failure = InitializationError("app-server initialization was cancelled")
                    await self._close_after_failed_initialization()
                    raise
                initialization_failed = True
            except Exception:
                initialization_failed = True
            if initialization_failed:
                self._state = "failed"
                self._failure = InitializationError("app-server initialization failed")
                await self._close_after_failed_initialization()
                raise self._failure
            self._session = AppServerSession(
                AppServerSession._CONSTRUCTION_TOKEN,
                self,
                self._engine,
                self._coordinator,
                self._session_capabilities(self._transport),
                self._generation,
            )
            self._failure = None
            self._state = "initialized"
            return self._session

    async def _initialize_engine(self, engine: _RpcEngine, identity: ClientIdentity) -> None:
        params = _decode_document(
            "v1/InitializeParams.json",
            {
                "clientInfo": identity.to_dict(),
                "capabilities": {
                    "experimentalApi": False,
                    "extensions": {},
                    "mcpServerOpenaiFormElicitation": False,
                    "optOutNotificationMethods": list(
                        _notification_optouts(self._compatibility.features)
                    ),
                    "requestAttestation": False,
                },
            },
        )
        result = await engine._initialize(params.to_dict())
        _decode_document("v1/InitializeResponse.json", result)
        await engine._send_initialized()

    def _session_capabilities(self, transport: ClientTransport) -> FeatureSet:
        return FeatureSet(
            requests=self._compatibility.features.requests,
            notifications=self._compatibility.features.notifications,
            callbacks=self._compatibility.features.callbacks,
            transports=frozenset({transport.capability}),
        )

    async def _close_after_failed_initialization(self) -> None:
        with suppress(TransportCleanupError):
            await self._engine.close()

    async def replace(
        self,
        transport: ClientTransport,
        *,
        backoff: BackoffHook | None = None,
    ) -> AppServerSession:
        self._validate_transport(transport, self._compatibility)
        if backoff is not None and not callable(backoff):
            raise TypeError("backoff must be callable or None")
        async with self._state_lock:
            if self._state == "initialized" and self._engine.failure is not None:
                self._state = "failed"
                self._failure = self._engine_failure()
            failed_generation = self._generation
            replacement_generation = failed_generation + 1
            if self._state != "failed" or self._identity is None:
                raise RestartError(
                    failed_generation=failed_generation,
                    replacement_generation=replacement_generation,
                    phase="precondition",
                )
            context = RestartContext(
                failed_generation=failed_generation,
                replacement_generation=replacement_generation,
                cause=self._engine_failure(),
            )
            if not self._replacement_transport_is_package_owned(transport):
                raise self._restart_error(context, "transport-lineage")
            delay = self._backoff_delay(backoff, context)
            lineage_failed = False
            try:
                proposed_lineage = self._proposed_transport_lineage(transport)
            except TypeError:
                lineage_failed = True
                proposed_lineage = None
            if lineage_failed or proposed_lineage is None:
                raise self._restart_error(context, "transport-lineage")
            if not self._lineages_are_available(proposed_lineage, required_capacity=2):
                raise self._restart_error(context, "transport-lineage")
            stale = StaleGenerationError(
                generation=failed_generation,
                current_generation=replacement_generation,
            )
            old_engine = self._engine
            old_coordinator = self._coordinator
            old_session = self._session
            self._state = "replacing"
            if old_session is not None:
                old_session._retire(stale)
            old_coordinator.retire(stale)
            old_cleanup_failed = False
            try:
                await self._retire_connection(old_engine, old_coordinator, stale)
            except asyncio.CancelledError:
                self._state = "failed"
                raise
            except Exception:
                old_cleanup_failed = True
            if old_cleanup_failed:
                self._state = "failed"
                self._failure = self._restart_error(context, "old-generation-cleanup")
                raise self._failure
            if delay:
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    self._state = "failed"
                    raise
            self._generation = replacement_generation
            self._session = None
            transport_start_failed = False
            transport_cleanup_unproven = False
            try:
                (
                    engine,
                    coordinator,
                    replacement_lineage,
                    replacement_channel_lineage,
                ) = await self._open_connection(
                    transport,
                    self._compatibility,
                    self._limits,
                    generation=replacement_generation,
                )
            except asyncio.CancelledError:
                self._state = "cleanup-failed"
                self._failure = self._restart_error(context, "transport-start-cancelled")
                raise
            except TransportCleanupError:
                transport_cleanup_unproven = True
                engine = coordinator = None
            except Exception:
                transport_start_failed = True
                engine = coordinator = None
            if transport_cleanup_unproven:
                self._state = "cleanup-failed"
                self._failure = self._restart_error(context, "transport-start-cleanup")
                raise self._failure
            if transport_start_failed or engine is None or coordinator is None:
                self._state = "failed"
                self._failure = self._restart_error(context, "transport-start")
                raise self._failure
            lineages_invalid = (
                replacement_lineage is not proposed_lineage
                or not self._lineages_are_available(
                    replacement_lineage, replacement_channel_lineage
                )
            )
            self._remember_connection_lineages(replacement_lineage, replacement_channel_lineage)
            if lineages_invalid:
                failure = self._restart_error(context, "transport-lineage")
                self._transport = transport
                self._engine = engine
                self._coordinator = coordinator
                self._state = "failed"
                self._failure = failure
                coordinator.retire(failure)
                cleanup_failed = False
                try:
                    await self._retain_retirement(engine, coordinator, failure)
                except Exception:
                    cleanup_failed = True
                _consume_current_cancellation()
                if cleanup_failed:
                    failure = self._restart_error(context, "replacement-cleanup")
                    self._failure = failure
                raise failure
            self._transport = transport
            self._engine = engine
            self._coordinator = coordinator
            self._state = "initializing"
            initialization_failed = False
            initialization_cancelled: asyncio.CancelledError | None = None
            cancellation_cleanup_failed = False
            try:
                await self._initialize_engine(engine, self._identity)
            except asyncio.CancelledError as error:
                if _current_task_is_cancelling():
                    initialization_cancelled = error
                    failure = self._restart_error(context, "initialization-cancelled")
                    self._state = "failed"
                    self._failure = failure
                    coordinator.retire(failure)
                    try:
                        await self._retain_retirement(engine, coordinator, failure)
                    except Exception:
                        cancellation_cleanup_failed = True
                else:
                    initialization_failed = True
            except Exception:
                initialization_failed = True
            if initialization_cancelled is not None:
                if cancellation_cleanup_failed:
                    _consume_current_cancellation()
                    failure = self._restart_error(context, "replacement-cleanup")
                    self._failure = failure
                    raise failure
                raise initialization_cancelled
            if initialization_failed:
                replacement_failure = self._restart_error(context, "initialization")
                self._state = "failed"
                self._failure = replacement_failure
                coordinator.retire(replacement_failure)
                cleanup_failed = False
                try:
                    await self._retain_retirement(engine, coordinator, replacement_failure)
                except Exception:
                    cleanup_failed = True
                _consume_current_cancellation()
                failure = (
                    self._restart_error(context, "replacement-cleanup")
                    if cleanup_failed
                    else replacement_failure
                )
                self._failure = failure
                raise failure
            self._session = AppServerSession(
                AppServerSession._CONSTRUCTION_TOKEN,
                self,
                engine,
                coordinator,
                self._session_capabilities(transport),
                replacement_generation,
            )
            self._state = "initialized"
            self._failure = None
            return self._session

    def _backoff_delay(self, backoff: BackoffHook | None, context: RestartContext) -> float:
        if backoff is None:
            return 0.0
        hook_failed = False
        try:
            delay = backoff(context)
        except asyncio.CancelledError:
            _consume_current_cancellation()
            hook_failed = True
            delay = 0.0
        except Exception:
            hook_failed = True
            delay = 0.0
        if hook_failed:
            raise self._restart_error(context, "backoff-hook")
        if inspect.iscoroutine(delay):
            delay.close()
            raise self._restart_error(context, "backoff-bound")
        if (
            type(delay) not in (int, float)
            or not _is_finite_number(delay)
            or delay < 0
            or delay > self._limits.max_backoff_seconds
        ):
            raise self._restart_error(context, "backoff-bound")
        return float(delay)

    @staticmethod
    def _restart_error(context: RestartContext, phase: str) -> RestartError:
        return RestartError(
            failed_generation=context.failed_generation,
            replacement_generation=context.replacement_generation,
            phase=phase,
        )

    def _engine_failure(self) -> AppServerClientError:
        if self._failure is not None:
            return self._failure
        failure = self._engine.failure
        if isinstance(failure, AppServerClientError):
            return failure
        return DisconnectedError("connection generation failed")

    @staticmethod
    async def _retire_connection(
        engine: _RpcEngine,
        coordinator: _AsyncCoordinator,
        failure: AppServerClientError,
    ) -> None:
        cleanup_failure: BaseException | None = None
        try:
            await engine.close(failure)
        except BaseException as error:
            cleanup_failure = error
        await engine.wait_quiescent()
        await coordinator.wait_quiescent()
        if cleanup_failure is not None:
            raise cleanup_failure

    @classmethod
    async def _retain_retirement(
        cls,
        engine: _RpcEngine,
        coordinator: _AsyncCoordinator,
        failure: AppServerClientError,
    ) -> None:
        retirement = asyncio.create_task(cls._retire_connection(engine, coordinator, failure))
        retirement_done = asyncio.Event()

        def finish_retirement(task: asyncio.Task[None]) -> None:
            _consume_task_exception(task)
            retirement_done.set()

        retirement.add_done_callback(finish_retirement)
        while not retirement_done.is_set():
            try:
                await retirement_done.wait()
            except asyncio.CancelledError:
                continue
        retirement.result()

    async def close(self) -> None:
        close_task = await self._select_close(None)
        await self._close_done.wait()
        close_task.result()

    async def _close_session(self, session: AppServerSession) -> None:
        close_task = await self._select_close(session)
        await self._close_done.wait()
        close_task.result()

    async def _select_close(self, session: AppServerSession | None) -> asyncio.Task[None]:
        async with self._state_lock:
            if session is not None:
                session._ensure_current()
            if self._state == "cleanup-failed":
                if self._failure is not None:
                    raise self._failure
                raise TransportCleanupError("client cleanup remains unproven")
            async with self._close_lock:
                if self._close_task is None:
                    self._state = "closing"
                    self._close_task = asyncio.create_task(self._run_close())
                    self._close_task.add_done_callback(self._finish_close)
                return self._close_task

    def _finish_close(self, task: asyncio.Task[None]) -> None:
        _consume_task_exception(task)
        self._close_done.set()

    async def _run_close(self) -> None:
        async with self._state_lock:
            self._state = "closed"
            self._coordinator.terminate(None)
            cleanup_failure: BaseException | None = None
            try:
                await self._engine.close(CallCancelledError("client closed"))
            except BaseException as error:
                cleanup_failure = error
            await self._engine.wait_quiescent()
            await self._coordinator.wait_quiescent()
            if cleanup_failure is not None:
                raise cleanup_failure

    async def _invalidate(self, session: AppServerSession, failure: JsonRpcValidationError) -> None:
        session._ensure_current()
        self._state = "failed"
        self._failure = failure
        await session._engine._fail(failure)


class AppServerSession:
    """One initialized generation exposing only the eight frozen typed operations."""

    _CONSTRUCTION_TOKEN = object()

    def __init__(
        self,
        token: object,
        client: AppServerClient,
        engine: _RpcEngine,
        coordinator: _AsyncCoordinator,
        capabilities: FeatureSet,
        generation: int,
    ) -> None:
        if token is not self._CONSTRUCTION_TOKEN:
            raise TypeError("sessions are created only by AppServerClient.initialize")
        self._client = client
        self._engine = engine
        self._coordinator = coordinator
        self._capabilities = capabilities
        self._generation = generation
        if engine._generation != generation or coordinator._generation != generation:
            raise SessionStateError("session generation must match its private owners")
        self._retired_failure: StaleGenerationError | None = None

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def capabilities(self) -> FeatureSet:
        return self._capabilities

    def _stale_error(self) -> StaleGenerationError:
        return StaleGenerationError(
            generation=self._generation,
            current_generation=self._client._generation,
        )

    def _retire(self, failure: StaleGenerationError) -> None:
        if self._retired_failure is None:
            self._retired_failure = failure

    def _ensure_current(self) -> None:
        if self._retired_failure is not None:
            raise self._retired_failure
        if self._generation != self._client._generation or self._client._session is not self:
            raise self._stale_error()

    def _ensure_active(self) -> None:
        self._ensure_current()
        if self._engine.failure is not None:
            self._client._state = "failed"
            self._client._failure = self._client._engine_failure()
        if self._client._state != "initialized":
            raise SessionStateError("typed operation requires an active initialized session")

    async def close(self) -> None:
        await self._client._close_session(self)

    async def events(self) -> AsyncIterator[ServerEvent]:
        self._ensure_current()
        async with aclosing(self._coordinator.events()) as events:
            async for event in events:
                self._ensure_current()
                yield event

    async def callbacks(self) -> AsyncIterator[ServerCallback]:
        self._ensure_current()
        async with aclosing(self._coordinator.callbacks()) as callbacks:
            async for callback in callbacks:
                self._ensure_current()
                yield callback

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
            result = await self._engine.call(
                capability,
                params.to_dict(),  # type: ignore[attr-defined]
                timeout=timeout,
            )
        except TimeoutError:
            self._ensure_current()
            raise CallTimeoutError(f"request timed out: {capability.value}") from None
        except Exception:
            self._ensure_current()
            if self._engine.failure is not None:
                await self._engine.wait_closed()
                self._ensure_current()
                self._client._state = "failed"
                self._client._failure = self._client._engine_failure()
            raise
        self._ensure_current()
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
            await self._client._invalidate(self, failure)
            raise failure
        self._ensure_current()
        return response
