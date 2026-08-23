#!/usr/bin/env python3
"""Verify the frozen app-server schema provenance and selected surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from schema_tree import schema_entries, tree_root

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = REPOSITORY_ROOT / "packages" / "codex-app-server-client" / "protocol"
MANIFEST_PATH = PROTOCOL_ROOT / "upstream-manifest.json"
SURFACE_PATH = PROTOCOL_ROOT / "supported-surface.json"
PUBLIC_API_PATH = PROTOCOL_ROOT / "public-api.json"
EXPECTED_UPSTREAM = {
    "repository": "https://github.com/openai/codex",
    "npm_distribution": "@openai/codex",
    "codex_version": "0.147.0",
    "source_tag": "rust-v0.147.0",
    "source_tag_object": "3ed6f04f6bf8b7c46299d1cb1ff99c74ce21a51d",
    "source_commit": "be6e8eac029b183056b7e4402879f15d2c85f61b",
}
EXPECTED_GENERATION = {
    "command": "codex app-server generate-json-schema --out <disposable-dir>",
    "wrapper_sha256": "134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477",
    "native_target": "aarch64-apple-darwin",
    "native_sha256": "19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37",
    "experimental": False,
}
EXPECTED_SCHEMA_ROOT = "eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa"
EXPECTED_SCHEMA_FILE_COUNT = 285
EXPECTED_SCHEMA_BYTES = 2_925_973
EXPECTED_SURFACE_ROOT = "9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f"
EXPECTED_PUBLIC_API_SHA256 = "11e02c9c460821ebd5dd08f80b6544eb45b2217a53b90918ca472c26d14e1a21"


def methods(union: dict[str, object]) -> set[str]:
    result: set[str] = set()
    for variant in union["oneOf"]:
        result.update(variant["properties"]["method"]["enum"])
    return result


def require_subset(label: str, selected: set[str], available: set[str]) -> None:
    missing = selected - available
    if missing:
        raise RuntimeError(f"{label} missing from retained schemas: {sorted(missing)}")


def surface_root(surface: dict[str, object]) -> str:
    content = dict(surface)
    del content["selected_surface_root"]
    encoded = json.dumps(content, separators=(",", ":"), sort_keys=True).encode() + b"\n"
    return hashlib.sha256(encoded).hexdigest()


def enum_values(api: dict[str, object], enum_name: str) -> set[str]:
    return set(api["capability_enums"][enum_name].values())


def require_schema_reference(schema_dir: Path, label: str, reference: str) -> None:
    relative, _, fragment = reference.partition("#")
    source = schema_dir / relative
    if not source.is_file():
        raise RuntimeError(f"{label} schema file is missing: {relative}")
    document = json.loads(source.read_text(encoding="utf-8"))
    if fragment:
        current: object = document
        for component in fragment.removeprefix("/").split("/"):
            if not isinstance(current, dict) or component not in current:
                raise RuntimeError(f"{label} schema fragment is missing: {reference}")
            current = current[component]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--surface", type=Path, default=SURFACE_PATH)
    parser.add_argument("--public-api", type=Path, default=PUBLIC_API_PATH)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    surface = json.loads(args.surface.read_text(encoding="utf-8"))
    api = json.loads(args.public_api.read_text(encoding="utf-8"))
    if manifest["upstream"] != EXPECTED_UPSTREAM:
        raise RuntimeError("frozen upstream identity changed")
    if manifest["generation"] != EXPECTED_GENERATION:
        raise RuntimeError("frozen schema generation identity changed")
    version = manifest["upstream"]["codex_version"]
    if surface["protocol"]["codex_version"] != version:
        raise RuntimeError("surface and upstream Codex versions differ")
    schema_dir = PROTOCOL_ROOT / "upstream" / version
    entries = schema_entries(schema_dir)
    recorded = manifest["schema_tree"]
    if entries != recorded["files"]:
        raise RuntimeError("retained schema file manifest mismatch")
    if tree_root(entries) != recorded["root_sha256"]:
        raise RuntimeError("retained schema tree root mismatch")
    if recorded["root_sha256"] != EXPECTED_SCHEMA_ROOT:
        raise RuntimeError("frozen schema tree root changed")
    if recorded["file_count"] != len(entries):
        raise RuntimeError("retained schema file count mismatch")
    if recorded["total_bytes"] != sum(int(entry["size"]) for entry in entries):
        raise RuntimeError("retained schema byte count mismatch")
    if recorded["file_count"] != EXPECTED_SCHEMA_FILE_COUNT:
        raise RuntimeError("frozen schema file count changed")
    if recorded["total_bytes"] != EXPECTED_SCHEMA_BYTES:
        raise RuntimeError("frozen schema byte count changed")

    calculated_surface_root = surface_root(surface)
    if calculated_surface_root != EXPECTED_SURFACE_ROOT:
        raise RuntimeError("frozen selected surface changed")
    if surface["selected_surface_root"]["sha256"] != EXPECTED_SURFACE_ROOT:
        raise RuntimeError("recorded selected-surface root mismatch")
    if api["selected_surface_root_sha256"] != EXPECTED_SURFACE_ROOT:
        raise RuntimeError("public API and selected-surface roots differ")
    if hashlib.sha256(args.public_api.read_bytes()).hexdigest() != EXPECTED_PUBLIC_API_SHA256:
        raise RuntimeError("frozen public API manifest changed")

    aggregate = json.loads((schema_dir / "codex_app_server_protocol.v2.schemas.json").read_text())
    server_requests = json.loads((schema_dir / "ServerRequest.json").read_text())
    client_notifications = json.loads((schema_dir / "ClientNotification.json").read_text())
    require_subset(
        "client requests",
        set(surface["client_requests"]["internal"])
        | set(surface["client_requests"]["public_typed"]),
        methods(aggregate["definitions"]["ClientRequest"]),
    )
    require_subset(
        "server notifications",
        set(surface["server_notifications"]["public_typed"]),
        methods(aggregate["definitions"]["ServerNotification"]),
    )
    require_subset(
        "server requests",
        set(surface["server_requests"]["public_policy_neutral"]),
        methods(server_requests),
    )
    require_subset(
        "client notifications",
        set(surface["client_notifications"]["internal"]),
        methods(client_notifications),
    )
    if surface["protocol"]["experimental_api"]:
        raise RuntimeError("experimental app-server API cannot be the baseline")
    if surface["capability_probe"]["raw_string_probe"]:
        raise RuntimeError("raw string capability probes are prohibited")

    public_requests = set(surface["client_requests"]["public_typed"])
    public_notifications = set(surface["server_notifications"]["public_typed"])
    public_callbacks = set(surface["server_requests"]["public_policy_neutral"])
    transports = set(surface["transports"]["supported"])
    if {
        value["protocol_method"] for value in api["session_operations"].values()
    } != public_requests:
        raise RuntimeError("public request operation map differs from selected surface")
    if set(api["notification_models"]) != public_notifications:
        raise RuntimeError("public notification model map differs from selected surface")
    if set(api["callback_models"]) != public_callbacks:
        raise RuntimeError("public callback model map differs from selected surface")
    if enum_values(api, "RequestCapability") != public_requests:
        raise RuntimeError("request capability enum differs from selected surface")
    if enum_values(api, "NotificationCapability") != public_notifications:
        raise RuntimeError("notification capability enum differs from selected surface")
    if enum_values(api, "CallbackCapability") != public_callbacks:
        raise RuntimeError("callback capability enum differs from selected surface")
    if enum_values(api, "TransportCapability") != transports:
        raise RuntimeError("transport capability enum differs from selected surface")
    for key, selected in {
        "requests": public_requests,
        "notifications": public_notifications,
        "callbacks": public_callbacks,
        "transports": transports,
    }.items():
        if set(surface["necessity"][key]) != selected:
            raise RuntimeError(f"necessity map differs from selected {key}")

    for model, reference in api["schema_models"].items():
        require_schema_reference(schema_dir, model, reference)
    for method, model in api["notification_models"].items():
        require_schema_reference(schema_dir, method, f"v2/{model}.json#")
    for method, callback in api["callback_models"].items():
        require_schema_reference(schema_dir, method, f"{callback['params']}.json#")
        require_schema_reference(schema_dir, method, f"{callback['response']}.json#")

    required_exports = {
        "__version__",
        "PINNED_PROTOCOL",
        "FeatureSet",
        "ByteChannel",
        "ClientTransport",
        "AppServerClient",
        "AppServerSession",
        "ServerEvent",
        "ServerCallback",
        *api["compatibility_functions"],
        *api["schema_models"],
        *api["notification_models"].values(),
        *api["capability_enums"],
        *api["configuration_models"],
        *api["errors"]["subclasses"],
        api["errors"]["base"],
        "StdioTransport",
        "UnixSocketTransport",
        "InjectedTransport",
        "TransportOwnership",
    }
    for callback in api["callback_models"].values():
        required_exports.update((callback["callback"], callback["params"], callback["response"]))
    root_exports = api["root_exports"]
    if len(root_exports) != len(set(root_exports)):
        raise RuntimeError("public root exports contain a duplicate")
    if set(root_exports) != required_exports:
        raise RuntimeError("public root exports differ from the exact API map")

    print(
        json.dumps(
            {
                "codex_version": version,
                "public_api_sha256": EXPECTED_PUBLIC_API_SHA256,
                "public_callbacks": len(public_callbacks),
                "public_notifications": len(public_notifications),
                "public_requests": len(public_requests),
                "schema_files": len(entries),
                "schema_root_sha256": tree_root(entries),
                "selected_surface_root_sha256": calculated_surface_root,
                "transports": sorted(transports),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
