"""Deterministic comparison of caller-supplied descriptive manifests."""

from __future__ import annotations

from .model import (
    CompatibilityReport,
    RuntimeManifest,
    UnavailableKind,
    UnavailableReason,
)


def _root(root) -> str:
    return f"sha256:{root.value}"


def compare_manifests(expected: RuntimeManifest, observed: RuntimeManifest) -> CompatibilityReport:
    """Compare exact required records while allowing unrelated observed extras."""

    if type(expected) is not RuntimeManifest or type(observed) is not RuntimeManifest:
        raise TypeError("expected and observed must be exact RuntimeManifest values")
    reasons: list[UnavailableReason] = []

    def add(kind: UnavailableKind, subject: str, wanted: str, actual: str | None) -> None:
        reasons.append(UnavailableReason(kind, subject, wanted, actual))

    if expected.component.name != observed.component.name:
        add(
            UnavailableKind.COMPONENT_NAME,
            expected.component.name,
            expected.component.name,
            observed.component.name,
        )
    if expected.component.version != observed.component.version:
        add(
            UnavailableKind.COMPONENT_VERSION,
            expected.component.name,
            expected.component.version,
            observed.component.version,
        )
    if expected.component.content_root != observed.component.content_root:
        add(
            UnavailableKind.COMPONENT_ROOT,
            expected.component.name,
            _root(expected.component.content_root),
            _root(observed.component.content_root),
        )

    observed_protocols = {protocol.name: protocol for protocol in observed.protocols}
    for protocol in expected.protocols:
        actual = observed_protocols.get(protocol.name)
        if actual is None:
            add(UnavailableKind.PROTOCOL_MISSING, protocol.name, protocol.version, None)
            continue
        if protocol.version != actual.version:
            add(
                UnavailableKind.PROTOCOL_VERSION,
                protocol.name,
                protocol.version,
                actual.version,
            )
        if protocol.schema_root != actual.schema_root:
            add(
                UnavailableKind.PROTOCOL_SCHEMA,
                protocol.name,
                _root(protocol.schema_root),
                _root(actual.schema_root),
            )
        for feature in sorted(set(protocol.features) - set(actual.features)):
            add(UnavailableKind.FEATURE_MISSING, f"{protocol.name}/{feature}", feature, None)

    observed_capabilities = {capability.name: capability for capability in observed.capabilities}
    for capability in expected.capabilities:
        actual = observed_capabilities.get(capability.name)
        if actual is None:
            add(UnavailableKind.CAPABILITY_MISSING, capability.name, capability.version, None)
        elif capability.version != actual.version:
            add(
                UnavailableKind.CAPABILITY_VERSION,
                capability.name,
                capability.version,
                actual.version,
            )

    observed_dependencies = {dependency.name: dependency for dependency in observed.dependencies}
    for dependency in expected.dependencies:
        actual = observed_dependencies.get(dependency.name)
        if actual is None:
            add(UnavailableKind.DEPENDENCY_MISSING, dependency.name, dependency.version, None)
            continue
        if dependency.version != actual.version:
            add(
                UnavailableKind.DEPENDENCY_VERSION,
                dependency.name,
                dependency.version,
                actual.version,
            )
        if dependency.content_root != actual.content_root:
            add(
                UnavailableKind.DEPENDENCY_ROOT,
                dependency.name,
                _root(dependency.content_root),
                _root(actual.content_root),
            )

    return CompatibilityReport(tuple(reasons))
