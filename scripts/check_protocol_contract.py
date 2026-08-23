#!/usr/bin/env python3
"""Verify the frozen app-server schema provenance and selected surface."""

from __future__ import annotations

import json
from pathlib import Path

from schema_tree import schema_entries, tree_root

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = REPOSITORY_ROOT / "packages" / "codex-app-server-client" / "protocol"
MANIFEST_PATH = PROTOCOL_ROOT / "upstream-manifest.json"
SURFACE_PATH = PROTOCOL_ROOT / "supported-surface.json"


def methods(union: dict[str, object]) -> set[str]:
    result: set[str] = set()
    for variant in union["oneOf"]:
        result.update(variant["properties"]["method"]["enum"])
    return result


def require_subset(label: str, selected: set[str], available: set[str]) -> None:
    missing = selected - available
    if missing:
        raise RuntimeError(f"{label} missing from retained schemas: {sorted(missing)}")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    surface = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
    version = manifest["upstream"]["codex_version"]
    schema_dir = PROTOCOL_ROOT / "upstream" / version
    entries = schema_entries(schema_dir)
    recorded = manifest["schema_tree"]
    if entries != recorded["files"]:
        raise RuntimeError("retained schema file manifest mismatch")
    if tree_root(entries) != recorded["root_sha256"]:
        raise RuntimeError("retained schema tree root mismatch")
    if recorded["file_count"] != len(entries):
        raise RuntimeError("retained schema file count mismatch")
    if recorded["total_bytes"] != sum(int(entry["size"]) for entry in entries):
        raise RuntimeError("retained schema byte count mismatch")

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

    print(
        json.dumps(
            {
                "codex_version": version,
                "public_callbacks": len(surface["server_requests"]["public_policy_neutral"]),
                "public_notifications": len(surface["server_notifications"]["public_typed"]),
                "public_requests": len(surface["client_requests"]["public_typed"]),
                "schema_files": len(entries),
                "schema_root_sha256": tree_root(entries),
                "transports": surface["transports"]["supported"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
