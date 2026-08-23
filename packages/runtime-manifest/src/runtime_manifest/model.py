"""Immutable descriptive runtime-manifest values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_NAME_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
MAX_PROTOCOLS = 32
MAX_FEATURES_PER_PROTOCOL = 32
MAX_CAPABILITIES = 64
MAX_DEPENDENCIES = 64
MAX_UNAVAILABLE_SUBJECT_LENGTH = 257
MAX_UNAVAILABLE_REASONS = (
    3 + MAX_PROTOCOLS * (2 + MAX_FEATURES_PER_PROTOCOL) + MAX_CAPABILITIES + 2 * MAX_DEPENDENCIES
)


class ManifestError(Exception):
    """Base error for runtime-manifest operations."""


class ManifestValidationError(ManifestError, ValueError):
    """A descriptive value violates the frozen schema."""


class ManifestDecodeError(ManifestError):
    """A serialized manifest cannot be decoded exactly."""


class UnsupportedSchemaError(ManifestDecodeError):
    """A manifest declares an unsupported schema version."""


def _require_name(value: str, field: str) -> None:
    if type(value) is not str:
        raise ManifestValidationError(f"{field} must be a string")
    if _NAME_PATTERN.fullmatch(value) is None:
        raise ManifestValidationError(f"{field} must be a bounded lowercase token")


def _require_text(value: str, field: str, *, max_length: int = 128) -> None:
    if type(value) is not str:
        raise ManifestValidationError(f"{field} must be a string")
    if (
        not value
        or len(value) > max_length
        or any(ord(character) < 32 or 0xD800 <= ord(character) <= 0xDFFF for character in value)
    ):
        raise ManifestValidationError(f"{field} must be bounded non-empty text")


@dataclass(frozen=True, slots=True)
class Sha256Root:
    """Exact lowercase SHA-256 content root."""

    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or _SHA256_PATTERN.fullmatch(self.value) is None:
            raise ManifestValidationError("SHA-256 root must be 64 lowercase hexadecimal digits")


@dataclass(frozen=True, slots=True)
class Component:
    """One exact descriptive component revision."""

    name: str
    version: str
    content_root: Sha256Root

    def __post_init__(self) -> None:
        _require_name(self.name, "component name")
        _require_text(self.version, "component version")
        if type(self.content_root) is not Sha256Root:
            raise ManifestValidationError("component content_root must be Sha256Root")


@dataclass(frozen=True, slots=True)
class Protocol:
    """One exact protocol/schema revision and its descriptive features."""

    name: str
    version: str
    schema_root: Sha256Root
    features: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_name(self.name, "protocol name")
        _require_text(self.version, "protocol version")
        if type(self.schema_root) is not Sha256Root:
            raise ManifestValidationError("protocol schema_root must be Sha256Root")
        if type(self.features) is not tuple:
            raise ManifestValidationError("protocol features must be an immutable tuple")
        for feature in self.features:
            _require_name(feature, "protocol feature")
        if len(self.features) > MAX_FEATURES_PER_PROTOCOL:
            raise ManifestValidationError(
                f"protocol features exceed the {MAX_FEATURES_PER_PROTOCOL}-item limit"
            )
        if len(set(self.features)) != len(self.features):
            raise ManifestValidationError("protocol features must be unique")
        object.__setattr__(self, "features", tuple(sorted(self.features)))


@dataclass(frozen=True, slots=True)
class Capability:
    """One exact descriptive capability revision."""

    name: str
    version: str

    def __post_init__(self) -> None:
        _require_name(self.name, "capability name")
        _require_text(self.version, "capability version")


def _sorted_unique_records(
    records: tuple[object, ...],
    record_type: type,
    field: str,
    maximum: int,
) -> tuple:
    if type(records) is not tuple:
        raise ManifestValidationError(f"{field} must be an immutable tuple")
    if len(records) > maximum:
        raise ManifestValidationError(f"{field} exceeds the {maximum}-item limit")
    if any(type(record) is not record_type for record in records):
        raise ManifestValidationError(f"{field} contains an invalid record")
    names = [record.name for record in records]
    if len(set(names)) != len(names):
        raise ManifestValidationError(f"{field} names must be unique")
    return tuple(sorted(records, key=lambda record: record.name))


@dataclass(frozen=True, slots=True)
class RuntimeManifest:
    """Caller-supplied descriptive metadata with no authority semantics."""

    component: Component
    protocols: tuple[Protocol, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    dependencies: tuple[Component, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.component) is not Component:
            raise ManifestValidationError("component must be an exact Component")
        if type(self.schema_version) is not int:
            raise ManifestValidationError("schema_version must be an integer")
        if self.schema_version != 1:
            raise UnsupportedSchemaError("unsupported runtime-manifest schema version")
        protocols = _sorted_unique_records(
            self.protocols,
            Protocol,
            "protocols",
            MAX_PROTOCOLS,
        )
        capabilities = _sorted_unique_records(
            self.capabilities,
            Capability,
            "capabilities",
            MAX_CAPABILITIES,
        )
        dependencies = _sorted_unique_records(
            self.dependencies,
            Component,
            "dependencies",
            MAX_DEPENDENCIES,
        )
        if any(dependency.name == self.component.name for dependency in dependencies):
            raise ManifestValidationError("component cannot depend on itself")
        object.__setattr__(self, "protocols", protocols)
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "dependencies", dependencies)


class UnavailableKind(StrEnum):
    """Closed descriptive mismatch categories."""

    COMPONENT_NAME = "component-name"
    COMPONENT_VERSION = "component-version"
    COMPONENT_ROOT = "component-root"
    PROTOCOL_MISSING = "protocol-missing"
    PROTOCOL_VERSION = "protocol-version"
    PROTOCOL_SCHEMA = "protocol-schema"
    FEATURE_MISSING = "feature-missing"
    CAPABILITY_MISSING = "capability-missing"
    CAPABILITY_VERSION = "capability-version"
    DEPENDENCY_MISSING = "dependency-missing"
    DEPENDENCY_VERSION = "dependency-version"
    DEPENDENCY_ROOT = "dependency-root"


@dataclass(frozen=True, slots=True)
class UnavailableReason:
    """One deterministic projection of unavailable descriptive compatibility."""

    kind: UnavailableKind
    subject: str
    expected: str
    observed: str | None

    def __post_init__(self) -> None:
        if type(self.kind) is not UnavailableKind:
            raise ManifestValidationError("unavailable kind must be exact")
        _require_text(
            self.subject,
            "unavailable subject",
            max_length=MAX_UNAVAILABLE_SUBJECT_LENGTH,
        )
        _require_text(self.expected, "unavailable expected value")
        if self.observed is not None:
            _require_text(self.observed, "unavailable observed value")


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    """Deterministic descriptive compatibility result."""

    unavailable_reasons: tuple[UnavailableReason, ...]

    def __post_init__(self) -> None:
        if type(self.unavailable_reasons) is not tuple or any(
            type(reason) is not UnavailableReason for reason in self.unavailable_reasons
        ):
            raise ManifestValidationError("unavailable_reasons must be an exact tuple")
        if len(set(self.unavailable_reasons)) != len(self.unavailable_reasons):
            raise ManifestValidationError("unavailable reasons must be unique")
        if len(self.unavailable_reasons) > MAX_UNAVAILABLE_REASONS:
            raise ManifestValidationError(
                f"unavailable reasons exceed the {MAX_UNAVAILABLE_REASONS}-item limit"
            )
        object.__setattr__(
            self,
            "unavailable_reasons",
            tuple(
                sorted(
                    self.unavailable_reasons,
                    key=lambda reason: (
                        reason.kind.value,
                        reason.subject,
                        reason.expected,
                        reason.observed or "",
                    ),
                )
            ),
        )

    @property
    def compatible(self) -> bool:
        """Whether no descriptive requirement is unavailable."""

        return not self.unavailable_reasons
