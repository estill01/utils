"""Immutable typed models for the explicitly selected frozen 0.162.1 schema graph."""

from .._model_registry import ModelRegistry
from ..compatibility import _packaged_protocol_root

_REGISTRY = ModelRegistry(
    _packaged_protocol_root().joinpath("profiles", "0.162.1", "upstream", "0.162.1"),
    __name__,
)
globals().update(_REGISTRY.namespace)
