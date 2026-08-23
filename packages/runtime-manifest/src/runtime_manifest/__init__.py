"""Deterministic, non-authoritative runtime compatibility metadata."""

from .compatibility import compare_manifests
from .model import (
    Capability,
    CompatibilityReport,
    Component,
    ManifestDecodeError,
    ManifestError,
    ManifestValidationError,
    Protocol,
    RuntimeManifest,
    Sha256Root,
    UnavailableKind,
    UnavailableReason,
    UnsupportedSchemaError,
)
from .serialization import canonical_json, parse_manifest

__version__ = "0.1.0"

__all__ = [
    "Capability",
    "CompatibilityReport",
    "Component",
    "ManifestDecodeError",
    "ManifestError",
    "ManifestValidationError",
    "Protocol",
    "RuntimeManifest",
    "Sha256Root",
    "UnavailableKind",
    "UnavailableReason",
    "UnsupportedSchemaError",
    "__version__",
    "canonical_json",
    "compare_manifests",
    "parse_manifest",
]
