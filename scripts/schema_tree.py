#!/usr/bin/env python3
"""Record or verify a deterministic official app-server schema tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schema_entries(schema_dir: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for file_path in sorted(path for path in schema_dir.rglob("*") if path.is_file()):
        data = file_path.read_bytes()
        json.loads(data)
        entries.append(
            {
                "path": file_path.relative_to(schema_dir).as_posix(),
                "sha256": sha256_bytes(data),
                "size": len(data),
            }
        )
    return entries


def tree_root(entries: list[dict[str, object]]) -> str:
    root_input = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries).encode()
    return sha256_bytes(root_input)


def build_manifest(args: argparse.Namespace) -> dict[str, object]:
    schema_dir = args.schema_dir.resolve()
    entries = schema_entries(schema_dir)
    if not entries:
        raise RuntimeError(f"schema directory is empty: {schema_dir}")
    return {
        "schema_version": 1,
        "upstream": {
            "repository": "https://github.com/openai/codex",
            "npm_distribution": "@openai/codex",
            "codex_version": args.codex_version,
            "source_tag": args.source_tag,
            "source_tag_object": args.source_tag_object,
            "source_commit": args.source_commit,
        },
        "generation": {
            "command": "codex app-server generate-json-schema --out <disposable-dir>",
            "wrapper_sha256": args.wrapper_sha256,
            "native_target": args.native_target,
            "native_sha256": args.native_sha256,
            "experimental": False,
        },
        "schema_tree": {
            "algorithm": (
                "sha256 of UTF-8 '<file-sha256>  <relative-path>\\n' lines sorted by relative path"
            ),
            "root_sha256": tree_root(entries),
            "file_count": len(entries),
            "total_bytes": sum(int(entry["size"]) for entry in entries),
            "files": entries,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--codex-version", required=True)
    parser.add_argument("--source-tag", required=True)
    parser.add_argument("--source-tag-object", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--wrapper-sha256", required=True)
    parser.add_argument("--native-target", required=True)
    parser.add_argument("--native-sha256", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest = build_manifest(args)
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.check:
        if args.manifest.read_text(encoding="utf-8") != encoded:
            raise RuntimeError(f"schema manifest is stale: {args.manifest}")
    else:
        args.manifest.write_text(encoded, encoding="utf-8")
    print(manifest["schema_tree"]["root_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
