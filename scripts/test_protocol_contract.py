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


def load(name: str) -> dict[str, object]:
    return json.loads((PROTOCOL_ROOT / name).read_text(encoding="utf-8"))


def expect_rejection(
    *,
    manifest: dict[str, object] | None = None,
    surface: dict[str, object] | None = None,
    api: dict[str, object] | None = None,
    message: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="utils-protocol-negative-") as temporary:
        temporary_root = Path(temporary)
        paths: dict[str, Path] = {}
        for key, value, source in (
            ("manifest", manifest, "upstream-manifest.json"),
            ("surface", surface, "supported-surface.json"),
            ("public-api", api, "public-api.json"),
        ):
            if value is not None:
                target = temporary_root / source
                target.write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                paths[key] = target
        command = [sys.executable, str(CHECKER)]
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

    print("5 protocol-contract mutations rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
