"""Policy-neutral generation replacement contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from .errors import AppServerClientError


@dataclass(frozen=True, slots=True)
class RestartContext:
    """Content-free facts supplied to one caller-owned backoff decision."""

    failed_generation: int
    replacement_generation: int
    cause: AppServerClientError

    def __post_init__(self) -> None:
        if (
            isinstance(self.failed_generation, bool)
            or not isinstance(self.failed_generation, int)
            or self.failed_generation < 1
        ):
            raise ValueError("failed_generation must be a positive integer")
        if (
            isinstance(self.replacement_generation, bool)
            or not isinstance(self.replacement_generation, int)
            or self.replacement_generation < 1
        ):
            raise ValueError("replacement_generation must be a positive integer")
        if self.replacement_generation != self.failed_generation + 1:
            raise ValueError("replacement_generation must immediately follow failed_generation")
        if not isinstance(self.cause, AppServerClientError):
            raise TypeError("cause must be AppServerClientError")


BackoffHook: TypeAlias = Callable[[RestartContext], float]


__all__ = ["BackoffHook", "RestartContext"]
