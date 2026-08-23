#!/usr/bin/env python3
"""Resolve changed repository paths to the package smoke jobs they require."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    mapping = json.loads((REPOSITORY_ROOT / "tools" / "changed_tests.json").read_text())
    packages = json.loads((REPOSITORY_ROOT / "tools" / "package_matrix.json").read_text())[
        "packages"
    ]

    selected: set[str] = set()
    for path in args.paths:
        normalized = path.lstrip("./")
        if any(
            normalized == prefix.rstrip("/") or normalized.startswith(prefix)
            for prefix in mapping["global_paths"]
        ):
            selected.update(packages)
        for prefix, names in mapping["package_paths"].items():
            if normalized == prefix.rstrip("/") or normalized.startswith(prefix):
                selected.update(names)
    print("\n".join(sorted(selected)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
