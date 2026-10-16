#!/usr/bin/env python3
"""Verify the frozen app-server schema provenance and selected surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from public_api_signatures import check_signatures
from schema_tree import schema_entries, tree_root

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = REPOSITORY_ROOT / "packages" / "codex-app-server-client" / "protocol"
MANIFEST_PATH = PROTOCOL_ROOT / "upstream-manifest.json"
SURFACE_PATH = PROTOCOL_ROOT / "supported-surface.json"
PUBLIC_API_PATH = PROTOCOL_ROOT / "public-api.json"
COMPATIBILITY_PATH = PROTOCOL_ROOT / "compatibility.json"
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
EXPECTED_PUBLIC_API_SHA256 = "0105415808843c26827a2a7356489b95a406dd59e66e181a7835f50ca9188f89"
EXPECTED_COMPATIBILITY = {
    "schema_version": 1,
    "codex_version": "0.147.0",
    "source_commit": "be6e8eac029b183056b7e4402879f15d2c85f61b",
    "schema_tree_root_sha256": EXPECTED_SCHEMA_ROOT,
    "semantic_schema_root_sha256": (
        "4e5c64213673b670d2575d7b7670d2089d49f92a92c56f2d16618e4a8857813e"
    ),
    "schema_file_count": EXPECTED_SCHEMA_FILE_COUNT,
    "schema_total_bytes": EXPECTED_SCHEMA_BYTES,
    "selected_surface_root_sha256": EXPECTED_SURFACE_ROOT,
    "public_api_sha256": EXPECTED_PUBLIC_API_SHA256,
}


MODERN_ROOT = PROTOCOL_ROOT / "profiles" / "0.162.1"
EXPECTED_MODERN_UPSTREAM = {
    "repository": "https://github.com/openai/codex",
    "npm_distribution": "@openai/codex",
    "codex_version": "0.162.1",
    "source_tag": "rust-v0.162.1",
    "source_tag_object": "7a078f6bb4ce0dc2a81408b334ce52979d92c603",
    "source_commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
}
EXPECTED_MODERN_ACQUISITION = {
    "kind": "official-source-precomputed-stable-json-schema",
    "bundle_path": (
        "codex-rs/app-server-protocol/schema/precomputed/app-server-exports-stable.json.zst"
    ),
    "bundle_sha256": "ed720775cdc264c7c5a930d582c56a27f5f8b18408187f783f93b9713ed40d48",
    "bundle_json_map": "json_schema",
    "checked_in_json_directory": "codex-rs/app-server-protocol/schema/json",
    "checked_in_json_byte_identical": True,
    "experimental": False,
    "codex_binary_executed": False,
    "binary_generation_evidence": None,
}
EXPECTED_MODERN_COMPATIBILITY = {
    "schema_version": 1,
    "codex_version": "0.162.1",
    "source_commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
    "schema_tree_root_sha256": ("56631e5e36c5d117bb21a2889708bee508127b340174a4719ee423468a5f7154"),
    "semantic_schema_root_sha256": (
        "a616a4522597421b8b790a65a0961bb3b22c73a918e8cc86fa39ef09ec7a243d"
    ),
    "schema_file_count": 317,
    "schema_total_bytes": 3_602_403,
    "selected_surface_root_sha256": (
        "4da1fd7f18a8e9a9809dcc0f46ae5b3d594c0a2028a1f5b1aacf9d410768d87a"
    ),
    "public_api_sha256": "661a39b475c5c1b62f9109a5caaaf3975416c97cbfbfad7159a8b604a9bc6193",
}
EXPECTED_SIGNATURE_HASHES = {
    "0.147.0": "caaf11fbf2b466f7e12db462affece06db6a1d1f77084294c64f500fe2456343",
    "0.156.1": "26d1ad5d864dfbaf604ba4052e29408e34a243c373b27307302d581d63331b5e",
    "0.162.1": "378de6c5383b6b170e0ff0c4aa13d40e1c786a177d59fe08b61227720e7eacdb",
}
PROFILES = {
    "0.147.0": (PROTOCOL_ROOT, EXPECTED_UPSTREAM, EXPECTED_COMPATIBILITY),
    "0.162.1": (MODERN_ROOT, EXPECTED_MODERN_UPSTREAM, EXPECTED_MODERN_COMPATIBILITY),
}


LOCAL_ROOT = PROTOCOL_ROOT / "profiles" / "0.156.1"
EXPECTED_LOCAL_UPSTREAM = {
    "codex_version": "0.156.1",
    "npm_distribution": "@openai/codex",
    "repository": "https://github.com/openai/codex",
    "source_commit": "b412ff32c417f855c2b2d1581b77058eed87c84b",
    "source_tag": "rust-v0.156.1",
    "source_tag_object": "81e8e29b2956dfe9b092c63953a9ed282781e77c",
}
EXPECTED_LOCAL_GENERATION = {
    "command": "codex app-server generate-json-schema --out <disposable-dir>",
    "experimental": False,
    "native_sha256": "0b2e9301d6100dddda3b9d5c80ebaeaa3a2f1962388f2f36f6b96a9f08b1f33f",
    "native_target": "x86_64-unknown-linux-musl",
    "wrapper_sha256": "0b2e9301d6100dddda3b9d5c80ebaeaa3a2f1962388f2f36f6b96a9f08b1f33f",
}
EXPECTED_LOCAL_COMPATIBILITY = {
    "codex_version": "0.156.1",
    "public_api_sha256": "06cf4e125a712e294121edaf8e3e59b973f87fe55e8b256c3fe7c8e072a9b13d",
    "schema_file_count": 310,
    "schema_total_bytes": 3513066,
    "schema_tree_root_sha256": "d66a1b1c52622a4f78fc87c9acf3a58e608e3ae53c308c455a9f49b9c9e0c248",
    "schema_version": 1,
    "selected_surface_root_sha256": (
        "bbcbb815d3ed76c54066dd1192cbd28748d5354f798d945c424c03a3a929fdc4"
    ),
    "semantic_schema_root_sha256": (
        "b960e4d0666a0f322af1cf192cec319a7914067eaac5c46cabc37d90769c50c7"
    ),
    "source_commit": "b412ff32c417f855c2b2d1581b77058eed87c84b",
}
PROFILES["0.156.1"] = (LOCAL_ROOT, EXPECTED_LOCAL_UPSTREAM, EXPECTED_LOCAL_COMPATIBILITY)


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


def check_profile(
    version: str,
    *,
    manifest_path: Path | None = None,
    surface_path: Path | None = None,
    public_api_path: Path | None = None,
    compatibility_path: Path | None = None,
    signatures_path: Path | None = None,
) -> dict[str, object]:
    profile_root, expected_upstream, expected = PROFILES[version]
    manifest_path = manifest_path or profile_root / "upstream-manifest.json"
    surface_path = surface_path or profile_root / "supported-surface.json"
    public_api_path = public_api_path or profile_root / "public-api.json"
    compatibility_path = compatibility_path or profile_root / "compatibility.json"
    signatures_path = signatures_path or profile_root / "public-api-signatures.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    surface = json.loads(surface_path.read_text(encoding="utf-8"))
    api = json.loads(public_api_path.read_text(encoding="utf-8"))
    compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise RuntimeError("frozen manifest format changed")
    if manifest["upstream"] != expected_upstream:
        raise RuntimeError("frozen upstream identity changed")
    if version == "0.147.0":
        if manifest.get("generation") != EXPECTED_GENERATION:
            raise RuntimeError("frozen schema generation identity changed")
    elif version == "0.156.1":
        if manifest.get("generation") != EXPECTED_LOCAL_GENERATION:
            raise RuntimeError("frozen local schema generation identity changed")
    elif "generation" in manifest or manifest.get("acquisition") != EXPECTED_MODERN_ACQUISITION:
        raise RuntimeError("frozen source-bundle acquisition identity changed")
    if compatibility != expected:
        raise RuntimeError("frozen compatibility metadata changed")
    version = manifest["upstream"]["codex_version"]
    if surface["protocol"]["codex_version"] != version:
        raise RuntimeError("surface and upstream Codex versions differ")
    schema_dir = profile_root / "upstream" / version
    entries = schema_entries(schema_dir)
    recorded = manifest["schema_tree"]
    if entries != recorded["files"]:
        raise RuntimeError("retained schema file manifest mismatch")
    if tree_root(entries) != recorded["root_sha256"]:
        raise RuntimeError("retained schema tree root mismatch")
    if recorded["root_sha256"] != expected["schema_tree_root_sha256"]:
        raise RuntimeError("frozen schema tree root changed")
    if recorded["file_count"] != len(entries):
        raise RuntimeError("retained schema file count mismatch")
    if recorded["total_bytes"] != sum(int(entry["size"]) for entry in entries):
        raise RuntimeError("retained schema byte count mismatch")
    if recorded["file_count"] != expected["schema_file_count"]:
        raise RuntimeError("frozen schema file count changed")
    if recorded["total_bytes"] != expected["schema_total_bytes"]:
        raise RuntimeError("frozen schema byte count changed")

    semantic_entries = []
    for entry in entries:
        document = json.loads((schema_dir / entry["path"]).read_bytes())
        canonical = json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        semantic_entries.append(
            {"path": entry["path"], "sha256": hashlib.sha256(canonical).hexdigest()}
        )
    if tree_root(semantic_entries) != expected["semantic_schema_root_sha256"]:
        raise RuntimeError("retained semantic schema tree root mismatch")

    calculated_surface_root = surface_root(surface)
    if calculated_surface_root != expected["selected_surface_root_sha256"]:
        raise RuntimeError("frozen selected surface changed")
    if surface["selected_surface_root"]["sha256"] != expected["selected_surface_root_sha256"]:
        raise RuntimeError("recorded selected-surface root mismatch")
    if api["selected_surface_root_sha256"] != expected["selected_surface_root_sha256"]:
        raise RuntimeError("public API and selected-surface roots differ")
    if hashlib.sha256(public_api_path.read_bytes()).hexdigest() != expected["public_api_sha256"]:
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
    if not public_requests <= enum_values(api, "RequestCapability"):
        raise RuntimeError("request capability enum differs from selected surface")
    if enum_values(api, "NotificationCapability") != public_notifications:
        raise RuntimeError("notification capability enum differs from selected surface")
    if enum_values(api, "CallbackCapability") != public_callbacks:
        raise RuntimeError("callback capability enum differs from selected surface")
    if not transports <= enum_values(api, "TransportCapability"):
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
        *api["errors"]["categories"],
        api["errors"]["base"],
        "StdioTransport",
        "UnixSocketTransport",
        "InjectedTransport",
        "TransportOwnership",
    }
    for callback in api["callback_models"].values():
        required_exports.update((callback["callback"], callback["params"], callback["response"]))
    expected_module = {
        "0.147.0": "codex_app_server_client",
        "0.162.1": "codex_app_server_client.v0_162_1",
        "0.156.1": "codex_app_server_client.v0_156_1",
    }[version]
    if version == "0.156.1":
        required_exports.add("LocalWebSocketTransport")
    if api["root_module"] != expected_module:
        raise RuntimeError("public API root module differs from the retained profile")
    root_exports = api["root_exports"]
    if len(root_exports) != len(set(root_exports)):
        raise RuntimeError("public root exports contain a duplicate")
    if set(root_exports) != required_exports:
        raise RuntimeError("public root exports differ from the exact API map")

    if (
        hashlib.sha256(signatures_path.read_bytes()).hexdigest()
        != EXPECTED_SIGNATURE_HASHES[version]
    ):
        raise RuntimeError("frozen public API signature fixture changed")
    check_signatures(profile_root, api)

    return {
        "codex_version": version,
        "provenance_kind": (
            "retained-binary-generation"
            if version in {"0.147.0", "0.156.1"}
            else EXPECTED_MODERN_ACQUISITION["kind"]
        ),
        "public_api_sha256": expected["public_api_sha256"],
        "public_callbacks": len(public_callbacks),
        "public_notifications": len(public_notifications),
        "public_requests": len(public_requests),
        "schema_files": len(entries),
        "schema_root_sha256": tree_root(entries),
        "selected_surface_root_sha256": calculated_surface_root,
        "public_api_signatures_verified": True,
        "transports": sorted(transports),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=(*PROFILES, "all"), default="all")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--surface", type=Path)
    parser.add_argument("--public-api", type=Path)
    parser.add_argument("--compatibility", type=Path)
    parser.add_argument("--signatures", type=Path)
    args = parser.parse_args()
    overrides = {
        "manifest_path": args.manifest,
        "surface_path": args.surface,
        "public_api_path": args.public_api,
        "compatibility_path": args.compatibility,
        "signatures_path": args.signatures,
    }
    if args.profile == "all" and any(overrides.values()):
        parser.error("fixture overrides require an explicit --profile")
    versions = PROFILES if args.profile == "all" else (args.profile,)
    results = [check_profile(version, **overrides) for version in versions]
    print(json.dumps(results if args.profile == "all" else results[0], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
