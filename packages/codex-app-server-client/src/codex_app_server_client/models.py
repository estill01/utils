"""Immutable typed models for the legacy frozen 0.147.0 schema graph."""

from ._model_registry import ModelRegistry
from .compatibility import PINNED_PROTOCOL, _packaged_protocol_root

_REGISTRY = ModelRegistry(
    _packaged_protocol_root().joinpath("upstream", PINNED_PROTOCOL.codex_version), __name__
)
globals().update(_REGISTRY.namespace)
