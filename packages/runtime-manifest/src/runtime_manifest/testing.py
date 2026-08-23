"""Neutral deterministic fixtures for runtime-manifest conformance."""

from __future__ import annotations

from .model import Capability, Component, Protocol, RuntimeManifest, Sha256Root

_A = "a" * 64
_B = "b" * 64
_C = "c" * 64
_D = "d" * 64
_E = "e" * 64


def neutral_expected() -> RuntimeManifest:
    return RuntimeManifest(
        component=Component("engine", "1.0", Sha256Root(_A)),
        protocols=(
            Protocol("events", "1", Sha256Root(_C), ("ordered",)),
            Protocol("wire", "1", Sha256Root(_B), ("cancel",)),
        ),
        capabilities=(Capability("lifecycle", "1"),),
        dependencies=(
            Component("codec", "1.0", Sha256Root(_C)),
            Component("queue", "1.0", Sha256Root(_D)),
        ),
    )


def neutral_observed() -> RuntimeManifest:
    return RuntimeManifest(
        component=Component("engine", "1.0", Sha256Root(_A)),
        protocols=(
            Protocol("events", "1", Sha256Root(_C), ("ordered", "replay")),
            Protocol("wire", "1", Sha256Root(_B), ("cancel", "status")),
        ),
        capabilities=(
            Capability("diagnostics", "1"),
            Capability("lifecycle", "1"),
        ),
        dependencies=(
            Component("codec", "1.0", Sha256Root(_C)),
            Component("queue", "1.0", Sha256Root(_D)),
            Component("storage", "1.0", Sha256Root(_E)),
        ),
    )


def neutral_incompatible() -> RuntimeManifest:
    return RuntimeManifest(
        component=Component("engine", "2.0", Sha256Root(_D)),
        protocols=(Protocol("wire", "2", Sha256Root(_E), ("status",)),),
        capabilities=(Capability("diagnostics", "1"),),
        dependencies=(Component("codec", "2.0", Sha256Root(_E)),),
    )


__all__ = ["neutral_expected", "neutral_incompatible", "neutral_observed"]
