"""Typed, domain-neutral Codex app-server client support."""

from .compatibility import (
    PINNED_PROTOCOL,
    BinaryIdentity,
    CompatibilityResult,
    ProtocolTarget,
    inspect_compatibility,
    resolve_codex_binary,
)
from .errors import (
    AmbiguousCodexBinaryError,
    AppServerClientError,
    CodexBinaryNotFoundError,
    CodexVersionError,
    SchemaMalformedError,
    SchemaMissingError,
    SchemaRootMismatchError,
    UnsupportedFeatureError,
)
from .surface import (
    CallbackCapability,
    FeatureSet,
    NotificationCapability,
    RequestCapability,
    TransportCapability,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "PINNED_PROTOCOL",
    "AmbiguousCodexBinaryError",
    "AppServerClientError",
    "BinaryIdentity",
    "CallbackCapability",
    "CodexBinaryNotFoundError",
    "CodexVersionError",
    "CompatibilityResult",
    "FeatureSet",
    "NotificationCapability",
    "ProtocolTarget",
    "RequestCapability",
    "SchemaMalformedError",
    "SchemaMissingError",
    "SchemaRootMismatchError",
    "TransportCapability",
    "UnsupportedFeatureError",
    "inspect_compatibility",
    "resolve_codex_binary",
]
