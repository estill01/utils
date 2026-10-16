#!/usr/bin/env python3
"""Exercise fail-closed mutations of the frozen protocol contract."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = REPOSITORY_ROOT / "packages" / "codex-app-server-client" / "protocol"
CHECKER = REPOSITORY_ROOT / "scripts" / "check_protocol_contract.py"


def load(name: str, profile: str = "0.147.0") -> dict[str, object]:
    root = PROTOCOL_ROOT if profile == "0.147.0" else PROTOCOL_ROOT / "profiles" / profile
    return json.loads((root / name).read_text(encoding="utf-8"))


def expect_rejection(
    *,
    manifest: dict[str, object] | None = None,
    surface: dict[str, object] | None = None,
    api: dict[str, object] | None = None,
    compatibility: dict[str, object] | None = None,
    signatures: dict[str, object] | None = None,
    profile: str = "0.147.0",
    message: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="utils-protocol-negative-") as temporary:
        temporary_root = Path(temporary)
        paths: dict[str, Path] = {}
        for key, value, source in (
            ("manifest", manifest, "upstream-manifest.json"),
            ("surface", surface, "supported-surface.json"),
            ("public-api", api, "public-api.json"),
            ("compatibility", compatibility, "compatibility.json"),
            ("signatures", signatures, "public-api-signatures.json"),
        ):
            if value is not None:
                target = temporary_root / source
                target.write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                paths[key] = target
        command = [sys.executable, str(CHECKER), "--profile", profile]
        for key, target in paths.items():
            command.extend((f"--{key}", str(target)))
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if completed.returncode == 0 or message not in completed.stdout:
            raise RuntimeError(f"mutation did not fail with {message!r}:\n{completed.stdout}")


def main() -> int:
    manifest = load("upstream-manifest.json")
    surface = load("supported-surface.json")
    api = load("public-api.json")

    changed_version = copy.deepcopy(manifest)
    changed_version["upstream"]["codex_version"] = "0.148.0"
    expect_rejection(
        manifest=changed_version,
        message="frozen upstream identity changed",
    )

    experimental = copy.deepcopy(manifest)
    experimental["generation"]["experimental"] = True
    expect_rejection(
        manifest=experimental,
        message="frozen schema generation identity changed",
    )

    changed_surface = copy.deepcopy(surface)
    changed_surface["client_requests"]["public_typed"].append("thread/fork")
    expect_rejection(
        surface=changed_surface,
        message="frozen selected surface changed",
    )

    missing_rationale = copy.deepcopy(surface)
    del missing_rationale["necessity"]["notifications"]["warning"]
    expect_rejection(
        surface=missing_rationale,
        message="frozen selected surface changed",
    )

    changed_api = copy.deepcopy(api)
    changed_api["compatibility_functions"]["raw_call"] = "(method: str) -> object"
    expect_rejection(
        api=changed_api,
        message="frozen public API manifest changed",
    )

    modern_manifest = load("upstream-manifest.json", "0.162.1")
    changed_source = copy.deepcopy(modern_manifest)
    changed_source["upstream"]["source_commit"] = "0" * 40
    expect_rejection(
        manifest=changed_source, profile="0.162.1", message="frozen upstream identity changed"
    )
    forged_generation = copy.deepcopy(modern_manifest)
    forged_generation["generation"] = {"command": "codex app-server generate-json-schema"}
    expect_rejection(
        manifest=forged_generation,
        profile="0.162.1",
        message="frozen source-bundle acquisition identity changed",
    )
    changed_bundle = copy.deepcopy(modern_manifest)
    changed_bundle["acquisition"]["bundle_sha256"] = "0" * 64
    expect_rejection(
        manifest=changed_bundle,
        profile="0.162.1",
        message="frozen source-bundle acquisition identity changed",
    )
    missing_schema = copy.deepcopy(modern_manifest)
    missing_schema["schema_tree"]["files"].pop()
    expect_rejection(
        manifest=missing_schema,
        profile="0.162.1",
        message="retained schema file manifest mismatch",
    )
    changed_modern_surface = load("supported-surface.json", "0.162.1")
    changed_modern_surface["client_requests"]["public_typed"].append("thread/fork")
    expect_rejection(
        surface=changed_modern_surface,
        profile="0.162.1",
        message="frozen selected surface changed",
    )
    changed_modern_api = load("public-api.json", "0.162.1")
    changed_modern_api["lifecycle"]["AppServerClient.connect"] = "async (**kwargs) -> object"
    expect_rejection(
        api=changed_modern_api, profile="0.162.1", message="frozen public API manifest changed"
    )
    changed_compatibility = load("compatibility.json", "0.162.1")
    changed_compatibility["public_api_sha256"] = "0" * 64
    expect_rejection(
        compatibility=changed_compatibility,
        profile="0.162.1",
        message="frozen compatibility metadata changed",
    )
    for version in ("0.147.0", "0.156.1", "0.162.1"):
        changed_signatures = load("public-api-signatures.json", version)
        changed_signatures["callables"]["AppServerClient.initialize"]["signature"] = "(identity)"
        expect_rejection(
            signatures=changed_signatures,
            profile=version,
            message="frozen public API signature fixture changed",
        )

    local_manifest = load("upstream-manifest.json", "0.156.1")
    local_manifest["generation"]["experimental"] = True
    expect_rejection(
        manifest=local_manifest,
        profile="0.156.1",
        message="frozen local schema generation identity changed",
    )
    local_surface = load("supported-surface.json", "0.156.1")
    local_surface["client_requests"]["public_typed"].remove("thread/turns/list")
    expect_rejection(
        surface=local_surface, profile="0.156.1", message="frozen selected surface changed"
    )
    print("17 protocol-contract mutations rejected across three retained profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
