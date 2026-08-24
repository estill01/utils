#!/usr/bin/env python3
"""Run the repository contract and exact pinned quality toolchain."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = json.loads((REPOSITORY_ROOT / "tools" / "toolchain.json").read_text())


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for the maintained quality envelope")
    actual = subprocess.run(
        [uv, "--version"],
        cwd=REPOSITORY_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    fields = actual.split(maxsplit=2)
    expected = str(TOOLCHAIN["uv"])
    if len(fields) < 2 or fields[0] != "uv" or fields[1] != expected:
        raise RuntimeError(
            f"uv version mismatch: expected semantic version {expected!r}, got {actual!r}"
        )

    run([sys.executable, "scripts/check_repo.py"])
    run(
        [
            sys.executable,
            "scripts/schema_tree.py",
            "--schema-dir",
            "packages/codex-app-server-client/protocol/upstream/0.147.0",
            "--manifest",
            "packages/codex-app-server-client/protocol/upstream-manifest.json",
            "--codex-version",
            "0.147.0",
            "--source-tag",
            "rust-v0.147.0",
            "--source-tag-object",
            "3ed6f04f6bf8b7c46299d1cb1ff99c74ce21a51d",
            "--source-commit",
            "be6e8eac029b183056b7e4402879f15d2c85f61b",
            "--wrapper-sha256",
            "134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477",
            "--native-target",
            "aarch64-apple-darwin",
            "--native-sha256",
            "19c4f144c5226a9f17c58e6f0fa854843b0f77a6eb420f40e2745a12f10f5d37",
            "--check",
        ]
    )
    run([sys.executable, "scripts/check_protocol_contract.py"])
    run([sys.executable, "scripts/test_protocol_contract.py"])
    run([sys.executable, "scripts/test_check_package.py"])
    run([sys.executable, "scripts/test_check_composition.py"])
    run([sys.executable, "scripts/test_check_qualification.py"])
    run(
        [
            sys.executable,
            "scripts/check_qualification.py",
            "--expected-head",
            args.expected_head,
        ]
    )
    ruff = f"ruff=={TOOLCHAIN['ruff']}"
    run([uv, "tool", "run", "--from", ruff, "ruff", "check", "."])
    run([uv, "tool", "run", "--from", ruff, "ruff", "format", "--check", "."])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
