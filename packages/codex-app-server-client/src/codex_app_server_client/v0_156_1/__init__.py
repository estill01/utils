"""Explicit stable Codex 0.156.1 facade; root imports remain on 0.147.0.

No automatic protocol selection, custom profile registry, or raw RPC escape.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import aclosing
from pathlib import Path
from types import MappingProxyType
from typing import TypeAlias

import codex_app_server_client as _legacy

from .. import __all__ as _legacy_exports
from .. import __version__ as __version__
from .. import compatibility as _compatibility
from .. import coordination as _coordination
from .. import session as _session
from .. import surface as _surface
from .. import transport as _transport
from ..compatibility import BinaryIdentity, CompatibilityResult, ProtocolTarget
from ..dispatch import DispatchRejectedError, dispatch_guard
from ..local_websocket import LocalWebSocketTransport
from ..restart import BackoffHook
from ..session import ClientLimits
from ..transport import ClientTransport
from . import models
from .coordination import (
    CommandExecutionApprovalCallback as CommandExecutionApprovalCallback,
)
from .coordination import (
    FileChangeApprovalCallback as FileChangeApprovalCallback,
)
from .coordination import (
    ServerCallback,
)
from .coordination import (
    UserInputCallback as UserInputCallback,
)

# Unchanged neutral errors, bounds, capabilities, and non-process transports.
for _name in _legacy_exports:
    if _name not in globals():
        globals()[_name] = getattr(_legacy, _name)
for _name in models.__all__:
    globals()[_name] = getattr(models, _name)

PINNED_PROTOCOL = _compatibility._PROTOCOL_0_156_1


def inspect_compatibility(
    binary: BinaryIdentity,
    target: ProtocolTarget = PINNED_PROTOCOL,
    *,
    schema_dir: Path | None = None,
) -> CompatibilityResult:
    """Inspect only this facade's retained exact protocol target."""
    if target != PINNED_PROTOCOL:
        raise _legacy.SchemaRootMismatchError("facade target differs from 0.156.1")
    return _compatibility.inspect_compatibility(binary, target, schema_dir=schema_dir)


class StdioTransport(_transport.StdioTransport):
    """Own one exact 0.156.1 executable, never a legacy-profile executable."""

    _PROTOCOL_TARGET = PINNED_PROTOCOL


class AppServerSession(_session.AppServerSession):
    """One immutable 0.156.1 generation using the shared lifecycle owner."""

    _CONSTRUCTION_TOKEN = object()

    async def list_items(
        self, params: models.ThreadItemsListParams, *, timeout: float | None = None
    ) -> models.ThreadItemsListResponse:
        if type(params) is not models.ThreadItemsListParams:
            raise TypeError("Use this profile's ThreadItemsListParams")
        if params.limit is None or not 1 <= params.limit <= 100:
            raise ValueError("Explicit item page limit must be between 1 and 100")
        if params.sortDirection not in ("asc", "desc"):
            raise ValueError("Select explicit item ordering")
        return await self._operation(
            _surface.RequestCapability.THREAD_ITEMS_LIST,
            params,
            models.ThreadItemsListParams,
            models.ThreadItemsListResponse,
            timeout,
        )

    async def list_turns(
        self, params: models.ThreadTurnsListParams, *, timeout: float | None = None
    ) -> models.ThreadTurnsListResponse:
        if type(params) is not models.ThreadTurnsListParams:
            raise TypeError("Use this profile's ThreadTurnsListParams")
        if params.limit is None or not 1 <= params.limit <= 100:
            raise ValueError("Explicit turn page limit must be between 1 and 100")
        if params.itemsView not in ("full", "summary", "notLoaded"):
            raise ValueError("Select explicit persisted item coverage")
        return await self._operation(
            _surface.RequestCapability.THREAD_TURNS_LIST,
            params,
            models.ThreadTurnsListParams,
            models.ThreadTurnsListResponse,
            timeout,
        )

    async def events(self) -> AsyncIterator[ServerEvent]:
        async with aclosing(super().events()) as events:
            async for event in events:
                yield event

    async def callbacks(self) -> AsyncIterator[ServerCallback]:
        async with aclosing(super().callbacks()) as callbacks:
            async for callback in callbacks:
                yield callback

    async def start_thread(
        self, params: models.ThreadStartParams, *, timeout: float | None = None
    ) -> models.ThreadStartResponse:
        return await self._operation(
            _surface.RequestCapability.THREAD_START,
            params,
            models.ThreadStartParams,
            models.ThreadStartResponse,
            timeout,
        )

    async def resume_thread(
        self, params: models.ThreadResumeParams, *, timeout: float | None = None
    ) -> models.ThreadResumeResponse:
        return await self._operation(
            _surface.RequestCapability.THREAD_RESUME,
            params,
            models.ThreadResumeParams,
            models.ThreadResumeResponse,
            timeout,
        )

    async def read_thread(
        self, params: models.ThreadReadParams, *, timeout: float | None = None
    ) -> models.ThreadReadResponse:
        return await self._operation(
            _surface.RequestCapability.THREAD_READ,
            params,
            models.ThreadReadParams,
            models.ThreadReadResponse,
            timeout,
        )

    async def list_threads(
        self, params: models.ThreadListParams, *, timeout: float | None = None
    ) -> models.ThreadListResponse:
        return await self._operation(
            _surface.RequestCapability.THREAD_LIST,
            params,
            models.ThreadListParams,
            models.ThreadListResponse,
            timeout,
        )

    async def start_turn(
        self, params: models.TurnStartParams, *, timeout: float | None = None
    ) -> models.TurnStartResponse:
        return await self._operation(
            _surface.RequestCapability.TURN_START,
            params,
            models.TurnStartParams,
            models.TurnStartResponse,
            timeout,
        )

    async def steer_turn(
        self, params: models.TurnSteerParams, *, timeout: float | None = None
    ) -> models.TurnSteerResponse:
        return await self._operation(
            _surface.RequestCapability.TURN_STEER,
            params,
            models.TurnSteerParams,
            models.TurnSteerResponse,
            timeout,
        )

    async def interrupt_turn(
        self, params: models.TurnInterruptParams, *, timeout: float | None = None
    ) -> models.TurnInterruptResponse:
        return await self._operation(
            _surface.RequestCapability.TURN_INTERRUPT,
            params,
            models.TurnInterruptParams,
            models.TurnInterruptResponse,
            timeout,
        )

    async def start_review(
        self, params: models.ReviewStartParams, *, timeout: float | None = None
    ) -> models.ReviewStartResponse:
        return await self._operation(
            _surface.RequestCapability.REVIEW_START,
            params,
            models.ReviewStartParams,
            models.ReviewStartResponse,
            timeout,
        )


_NOTIFICATION_TYPES = MappingProxyType(
    {
        capability: getattr(models, model.__name__)
        for capability, model in _coordination._NOTIFICATION_TYPES.items()
    }
)
_CALLBACK_SPECS = MappingProxyType(
    {
        capability: (
            getattr(models, params.__name__),
            getattr(models, response.__name__),
            globals()[callback.__name__],
        )
        for capability, (params, response, callback) in _coordination._CALLBACK_SPECS.items()
    }
)
ServerEvent: TypeAlias = (
    models.ErrorNotification
    | models.WarningNotification
    | models.DeprecationNoticeNotification
    | models.ThreadStartedNotification
    | models.ThreadStatusChangedNotification
    | models.ThreadClosedNotification
    | models.TurnStartedNotification
    | models.TurnCompletedNotification
    | models.TurnDiffUpdatedNotification
    | models.TurnPlanUpdatedNotification
    | models.ItemStartedNotification
    | models.ItemCompletedNotification
    | models.AgentMessageDeltaNotification
    | models.PlanDeltaNotification
    | models.ReasoningSummaryTextDeltaNotification
)
_BINDING = _session._SessionBinding(
    target=PINNED_PROTOCOL,
    models=models._REGISTRY.namespace,
    decode_document=models._REGISTRY.decode_document,
    notification_types=_NOTIFICATION_TYPES,
    callback_specs=_CALLBACK_SPECS,
    stdio_type=StdioTransport,
    session_type=AppServerSession,
)


class AppServerClient(_session.AppServerClient):
    """Explicit 0.156.1 client sharing bounded RPC and lifecycle machinery."""

    _CONSTRUCTION_TOKEN = object()

    @classmethod
    def _binding(cls) -> _session._SessionBinding:
        return _BINDING

    @classmethod
    async def connect(
        cls,
        transport: ClientTransport,
        compatibility: CompatibilityResult,
        *,
        limits: ClientLimits = _session._DEFAULT_CLIENT_LIMITS,
    ) -> AppServerClient:
        return await super().connect(transport, compatibility, limits=limits)

    async def initialize(self, identity: models.ClientIdentity) -> AppServerSession:
        return await super().initialize(identity)

    async def replace(
        self, transport: ClientTransport, *, backoff: BackoffHook | None = None
    ) -> AppServerSession:
        return await super().replace(transport, backoff=backoff)


__all__ = [
    *_legacy_exports,
    "ThreadTurnsListParams",
    "ThreadTurnsListResponse",
    "ThreadItemsListParams",
    "ThreadItemsListResponse",
    "LocalWebSocketTransport",
    "DispatchRejectedError",
    "dispatch_guard",
]
