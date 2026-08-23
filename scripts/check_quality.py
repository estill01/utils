#!/usr/bin/env python3
"""Run the repository contract and exact pinned quality toolchain."""

from __future__ import annotations

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
    ruff = f"ruff=={TOOLCHAIN['ruff']}"
    run([uv, "tool", "run", "--from", ruff, "ruff", "check", "."])
    run([uv, "tool", "run", "--from", ruff, "ruff", "format", "--check", "."])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
