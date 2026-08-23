"""Neutral embedded and service lifecycle contracts."""

from .conformance import (
    ConformanceError,
    ConformanceFixture,
    ConformanceReport,
    assert_lifecycle_conformance,
)
from .contract import (
    Cancelled,
    CancelResult,
    EventRecord,
    Failed,
    HostContract,
    HostShape,
    InvalidCursorError,
    LifecycleContractError,
    LifecycleHost,
    RunRef,
    RunState,
    RunStatus,
    Succeeded,
    UnknownRunError,
)

__version__ = "0.1.0"

__all__ = [
    "CancelResult",
    "Cancelled",
    "ConformanceError",
    "ConformanceFixture",
    "ConformanceReport",
    "EventRecord",
    "Failed",
    "HostContract",
    "HostShape",
    "InvalidCursorError",
    "LifecycleContractError",
    "LifecycleHost",
    "RunRef",
    "RunState",
    "RunStatus",
    "Succeeded",
    "UnknownRunError",
    "__version__",
    "assert_lifecycle_conformance",
]
