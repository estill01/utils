"""Typed callbacks for the exact 0.156.1 model graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

from ..coordination import _CallbackState
from . import models


@dataclass(frozen=True, slots=True, init=False)
class CommandExecutionApprovalCallback:
    """One caller-authorized, generation-bound command approval callback."""

    params: models.CommandExecutionRequestApprovalParams
    _state: _CallbackState = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("callbacks are created only by an active session")

    async def respond(self, response: models.CommandExecutionRequestApprovalResponse) -> None:
        await self._state.owner.respond(
            self._state, response, models.CommandExecutionRequestApprovalResponse
        )


@dataclass(frozen=True, slots=True, init=False)
class FileChangeApprovalCallback:
    """One caller-authorized, generation-bound file change callback."""

    params: models.FileChangeRequestApprovalParams
    _state: _CallbackState = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("callbacks are created only by an active session")

    async def respond(self, response: models.FileChangeRequestApprovalResponse) -> None:
        await self._state.owner.respond(
            self._state, response, models.FileChangeRequestApprovalResponse
        )


@dataclass(frozen=True, slots=True, init=False)
class UserInputCallback:
    """One caller-authorized, generation-bound user input callback."""

    params: models.ToolRequestUserInputParams
    _state: _CallbackState = field(repr=False, compare=False)

    def __init__(self) -> None:
        raise TypeError("callbacks are created only by an active session")

    async def respond(self, response: models.ToolRequestUserInputResponse) -> None:
        await self._state.owner.respond(self._state, response, models.ToolRequestUserInputResponse)


ServerCallback: TypeAlias = (
    CommandExecutionApprovalCallback | FileChangeApprovalCallback | UserInputCallback
)
