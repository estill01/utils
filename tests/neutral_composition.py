#!/usr/bin/env python3
"""One test-only, domain-neutral composition of the three installed wheels."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import codex_app_server_client as client_api
import embedded_service_contract as lifecycle_api
import embedded_service_contract.testing as lifecycle_testing
import runtime_manifest as manifest_api

APP_SERVER_CLIENT = client_api.AppServerClient
BINARY_IDENTITY = client_api.BinaryIdentity
CLIENT_IDENTITY = client_api.ClientIdentity
CLIENT_INJECTED_TRANSPORT = client_api.InjectedTransport
CLIENT_PINNED_PROTOCOL = client_api.PINNED_PROTOCOL
CLIENT_THREAD_LIST_PARAMS = client_api.ThreadListParams
CLIENT_TRANSPORT_OWNERSHIP = client_api.TransportOwnership
CLIENT_EXPORTS = client_api.__all__
CLIENT_MODULE = client_api.__name__
CLIENT_VERSION = client_api.__version__
INSPECT_CLIENT_COMPATIBILITY = client_api.inspect_compatibility

HOST_SHAPE = lifecycle_api.HostShape
LIFECYCLE_EXPORTS = lifecycle_api.__all__
LIFECYCLE_MODULE = lifecycle_api.__name__
LIFECYCLE_VERSION = lifecycle_api.__version__
ASSERT_LIFECYCLE_CONFORMANCE = lifecycle_api.assert_lifecycle_conformance

LIFECYCLE_TESTING_EXPORTS = lifecycle_testing.__all__
LIFECYCLE_TESTING_MODULE = lifecycle_testing.__name__
EMBEDDED_FIXTURE = lifecycle_testing.embedded_fixture
SERVICE_FIXTURE = lifecycle_testing.service_fixture

MANIFEST_CAPABILITY = manifest_api.Capability
MANIFEST_COMPONENT = manifest_api.Component
MANIFEST_PROTOCOL = manifest_api.Protocol
RUNTIME_MANIFEST = manifest_api.RuntimeManifest
SHA256_ROOT = manifest_api.Sha256Root
UNAVAILABLE_KIND = manifest_api.UnavailableKind
MANIFEST_EXPORTS = manifest_api.__all__
MANIFEST_MODULE = manifest_api.__name__
MANIFEST_VERSION = manifest_api.__version__
CANONICAL_JSON = manifest_api.canonical_json
COMPARE_MANIFESTS = manifest_api.compare_manifests
PARSE_MANIFEST = manifest_api.parse_manifest

PACKAGE_NAMES = (
    "codex-app-server-client",
    "embedded-service-contract",
    "runtime-manifest",
)
ROOT_FIELDS = {"version", "wheel_content_root_sha256"}
PROTOCOL_FIELDS = {
    "version",
    "schema_root_sha256",
    "selected_surface_root_sha256",
}


def require_sha256(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"{label} must be an exact lowercase SHA-256 value")
    return value


def load_inputs(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict or set(value) != {
        "schema_version",
        "manifest_sha256",
        "packages",
        "protocol",
    }:
        raise RuntimeError("composition input has an unexpected top-level shape")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise RuntimeError("composition input has an unsupported schema version")
    require_sha256(value["manifest_sha256"], "canonical manifest")
    packages = value["packages"]
    if type(packages) is not dict or set(packages) != set(PACKAGE_NAMES):
        raise RuntimeError("composition input package set is not exact")
    for name in PACKAGE_NAMES:
        record = packages[name]
        if type(record) is not dict or set(record) != ROOT_FIELDS:
            raise RuntimeError(f"composition input package record is not exact: {name}")
        if type(record["version"]) is not str or not record["version"]:
            raise RuntimeError(f"composition input package version is invalid: {name}")
        require_sha256(record["wheel_content_root_sha256"], f"{name} content root")
    protocol = value["protocol"]
    if type(protocol) is not dict or set(protocol) != PROTOCOL_FIELDS:
        raise RuntimeError("composition input protocol record is not exact")
    if type(protocol["version"]) is not str or not protocol["version"]:
        raise RuntimeError("composition input protocol version is invalid")
    require_sha256(protocol["schema_root_sha256"], "protocol schema root")
    require_sha256(protocol["selected_surface_root_sha256"], "protocol surface root")
    return value


def require_public_surface() -> tuple[str, ...]:
    requirements = (
        (
            CLIENT_MODULE,
            CLIENT_EXPORTS,
            {
                "AppServerClient",
                "BinaryIdentity",
                "ClientIdentity",
                "InjectedTransport",
                "PINNED_PROTOCOL",
                "ThreadListParams",
                "TransportOwnership",
                "inspect_compatibility",
            },
        ),
        (
            LIFECYCLE_MODULE,
            LIFECYCLE_EXPORTS,
            {"HostShape", "assert_lifecycle_conformance"},
        ),
        (
            LIFECYCLE_TESTING_MODULE,
            LIFECYCLE_TESTING_EXPORTS,
            {"embedded_fixture", "service_fixture"},
        ),
        (
            MANIFEST_MODULE,
            MANIFEST_EXPORTS,
            {
                "Capability",
                "Component",
                "Protocol",
                "RuntimeManifest",
                "Sha256Root",
                "UnavailableKind",
                "canonical_json",
                "compare_manifests",
                "parse_manifest",
            },
        ),
    )
    reached: list[str] = []
    for module_name, exports, names in requirements:
        missing = sorted(names - set(exports))
        if missing:
            raise RuntimeError(f"installed public surface is missing names: {missing}")
        reached.append(module_name)
    return tuple(reached)


class DeterministicChannel:
    """A test-only injected JSON-lines peer with no process or network owner."""

    def __init__(self) -> None:
        self.incoming: asyncio.Queue[bytes] = asyncio.Queue()
        self.initialized = False
        self.close_count = 0

    def queue(self, value: dict[str, object]) -> None:
        self.incoming.put_nowait(
            json.dumps(value, separators=(",", ":"), sort_keys=True).encode() + b"\n"
        )

    async def read_line(self, *, max_bytes: int) -> bytes:
        value = await self.incoming.get()
        if len(value) > max_bytes:
            raise RuntimeError("deterministic channel response exceeded the client limit")
        return value

    async def write_line(self, data: bytes) -> None:
        value = json.loads(data)
        if type(value) is not dict:
            raise RuntimeError("deterministic channel received a non-object envelope")
        method = value.get("method")
        if method == "initialize" and "id" in value:
            self.queue(
                {
                    "id": value["id"],
                    "result": {
                        "codexHome": "/neutral/codex-home",
                        "platformFamily": "unix",
                        "platformOs": "macos",
                        "userAgent": "utils-neutral-composition",
                    },
                }
            )
            return
        if method == "initialized" and "id" not in value:
            self.initialized = True
            return
        if method == "thread/list" and "id" in value:
            self.queue({"id": value["id"], "result": {"data": []}})
            return
        raise RuntimeError("deterministic channel received an unsupported envelope")

    async def close(self) -> None:
        self.close_count += 1


def package_component(inputs: dict[str, object], name: str) -> object:
    packages = inputs["packages"]
    assert isinstance(packages, dict)
    record = packages[name]
    assert isinstance(record, dict)
    return MANIFEST_COMPONENT(
        name,
        str(record["version"]),
        SHA256_ROOT(str(record["wheel_content_root_sha256"])),
    )


def runtime_manifest(inputs: dict[str, object], *, mismatch: str | None = None) -> object:
    protocol = inputs["protocol"]
    assert isinstance(protocol, dict)
    dependencies = (
        package_component(inputs, "embedded-service-contract"),
        package_component(inputs, "runtime-manifest"),
    )
    surface_root = str(protocol["selected_surface_root_sha256"])
    if mismatch == "protocol-schema":
        surface_root = "0" * 64
    elif mismatch == "dependency-root":
        embedded = dependencies[0]
        dependencies = (
            MANIFEST_COMPONENT(
                embedded.name,
                embedded.version,
                SHA256_ROOT("0" * 64),
            ),
            dependencies[1],
        )
    elif mismatch is not None:
        raise RuntimeError(f"unknown neutral mismatch fixture: {mismatch}")
    return RUNTIME_MANIFEST(
        component=package_component(inputs, "codex-app-server-client"),
        protocols=(
            MANIFEST_PROTOCOL(
                "codex-app-server-schema",
                str(protocol["version"]),
                SHA256_ROOT(str(protocol["schema_root_sha256"])),
            ),
            MANIFEST_PROTOCOL(
                "codex-app-server-surface",
                str(protocol["version"]),
                SHA256_ROOT(surface_root),
                ("typed-session",),
            ),
        ),
        capabilities=(
            MANIFEST_CAPABILITY("embedded-lifecycle", "1"),
            MANIFEST_CAPABILITY("injected-byte-channel", "1"),
            MANIFEST_CAPABILITY("service-lifecycle", "1"),
        ),
        dependencies=dependencies,
    )


async def run_client(inputs: dict[str, object]) -> dict[str, object]:
    packages = inputs["packages"]
    protocol = inputs["protocol"]
    assert isinstance(packages, dict)
    assert isinstance(protocol, dict)
    installed_versions = {
        "codex-app-server-client": CLIENT_VERSION,
        "embedded-service-contract": LIFECYCLE_VERSION,
        "runtime-manifest": MANIFEST_VERSION,
    }
    expected_versions = {name: record["version"] for name, record in packages.items()}
    if installed_versions != expected_versions:
        raise RuntimeError("installed package versions differ from composition inputs")
    target = CLIENT_PINNED_PROTOCOL
    if (
        target.codex_version != protocol["version"]
        or target.schema_tree_root_sha256 != protocol["schema_root_sha256"]
        or target.selected_surface_root_sha256 != protocol["selected_surface_root_sha256"]
    ):
        raise RuntimeError("installed app-server protocol roots differ from composition inputs")
    compatibility = INSPECT_CLIENT_COMPATIBILITY(
        BINARY_IDENTITY(
            path=Path("/neutral/non-executed-codex"),
            reported_version=target.codex_version,
            sha256="0" * 64,
        )
    )
    channel = DeterministicChannel()
    client = await APP_SERVER_CLIENT.connect(
        CLIENT_INJECTED_TRANSPORT(
            channel,
            ownership=CLIENT_TRANSPORT_OWNERSHIP.OWNED,
        ),
        compatibility,
    )
    session = await client.initialize(CLIENT_IDENTITY("neutral-composition", "1"))
    listed = await session.list_threads(CLIENT_THREAD_LIST_PARAMS(), timeout=1.0)
    await session.close()
    if not channel.initialized or channel.close_count != 1:
        raise RuntimeError("deterministic channel lifecycle did not close exactly once")
    return {
        "channel_close_count": channel.close_count,
        "generation": session.generation,
        "listed_threads": len(listed.data),
        "transport": "injected-byte-channel",
    }


async def compose(inputs: dict[str, object]) -> dict[str, object]:
    public_modules = require_public_surface()
    embedded_fixture = EMBEDDED_FIXTURE()
    service_fixture = SERVICE_FIXTURE()
    embedded = ASSERT_LIFECYCLE_CONFORMANCE(embedded_fixture)
    service = ASSERT_LIFECYCLE_CONFORMANCE(service_fixture)
    embedded_contract = embedded_fixture.host_factory("owner-audit").contract
    service_contract = service_fixture.host_factory("owner-audit").contract
    if embedded_contract.process_owner_count + service_contract.process_owner_count != 1:
        raise RuntimeError("neutral composition must declare exactly one process owner")
    if embedded.shape is not HOST_SHAPE.EMBEDDED or service.shape is not HOST_SHAPE.SERVICE:
        raise RuntimeError("neutral lifecycle shapes differ")

    expected = runtime_manifest(inputs)
    encoded = CANONICAL_JSON(expected)
    manifest_sha256 = hashlib.sha256(encoded.encode()).hexdigest()
    if manifest_sha256 != inputs["manifest_sha256"]:
        raise RuntimeError("canonical neutral manifest shape differs from composition inputs")
    observed = PARSE_MANIFEST(encoded)
    compatible = COMPARE_MANIFESTS(expected, observed)
    if not compatible.compatible:
        raise RuntimeError("exact neutral composition manifest is incompatible")
    dependency_incompatible = COMPARE_MANIFESTS(
        expected,
        runtime_manifest(inputs, mismatch="dependency-root"),
    )
    protocol_incompatible = COMPARE_MANIFESTS(
        expected,
        runtime_manifest(inputs, mismatch="protocol-schema"),
    )

    def diagnostic(reason: object) -> dict[str, object]:
        return {
            "expected": reason.expected,
            "kind": reason.kind.value,
            "observed": reason.observed,
            "subject": reason.subject,
        }

    dependency_diagnostics = [
        diagnostic(reason) for reason in dependency_incompatible.unavailable_reasons
    ]
    protocol_diagnostics = [
        diagnostic(reason) for reason in protocol_incompatible.unavailable_reasons
    ]
    packages = inputs["packages"]
    protocol = inputs["protocol"]
    assert isinstance(packages, dict)
    assert isinstance(protocol, dict)
    embedded_record = packages["embedded-service-contract"]
    assert isinstance(embedded_record, dict)
    if dependency_diagnostics != [
        {
            "expected": f"sha256:{embedded_record['wheel_content_root_sha256']}",
            "kind": UNAVAILABLE_KIND.DEPENDENCY_ROOT.value,
            "observed": f"sha256:{'0' * 64}",
            "subject": "embedded-service-contract",
        }
    ]:
        raise RuntimeError("dependency-root mismatch did not produce one exact typed diagnostic")
    if protocol_diagnostics != [
        {
            "expected": f"sha256:{protocol['selected_surface_root_sha256']}",
            "kind": UNAVAILABLE_KIND.PROTOCOL_SCHEMA.value,
            "observed": f"sha256:{'0' * 64}",
            "subject": "codex-app-server-surface",
        }
    ]:
        raise RuntimeError("protocol-root mismatch did not produce one exact typed diagnostic")
    return {
        "client": await run_client(inputs),
        "incompatible_root_diagnostics": dependency_diagnostics + protocol_diagnostics,
        "lifecycle": {
            "embedded": {
                "events": embedded.observed_events,
                "scenarios": embedded.scenarios,
                "shape": embedded.shape.value,
            },
            "process_owner_count": (
                embedded_contract.process_owner_count + service_contract.process_owner_count
            ),
            "service": {
                "events": service.observed_events,
                "scenarios": service.scenarios,
                "shape": service.shape.value,
            },
        },
        "manifest_compatible": compatible.compatible,
        "manifest_sha256": manifest_sha256,
        "packages": {name: record["version"] for name, record in packages.items()},
        "protocol": protocol,
        "public_modules": list(public_modules),
        "schema_version": 1,
    }


def main() -> int:
    if len(sys.argv) != 2:
        raise RuntimeError("neutral composition requires one exact input file")
    result = asyncio.run(compose(load_inputs(Path(sys.argv[1]))))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
