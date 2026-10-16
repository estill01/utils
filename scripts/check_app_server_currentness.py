#!/usr/bin/env python3
"""Run one bounded official-binary schema currentness check."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import codex_app_server_client
from codex_app_server_client import v0_156_1, v0_162_1
from codex_app_server_client.compatibility import _generate_schema_tree


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", required=True)
    parser.add_argument("--profile", choices=("0.147.0", "0.156.1", "0.162.1"), default="0.147.0")
    parser.add_argument(
        "--schema-dir",
        type=Path,
        help="Reuse this exact retained native generation instead of generating again",
    )
    args = parser.parse_args()
    api = {"0.147.0": codex_app_server_client, "0.156.1": v0_156_1, "0.162.1": v0_162_1}[
        args.profile
    ]
    binary = api.resolve_codex_binary(args.codex)
    with tempfile.TemporaryDirectory(prefix="utils-codex-schema-currentness-") as temporary:
        schema_dir = args.schema_dir or Path(temporary) / "schema"
        if args.schema_dir is None:
            _generate_schema_tree(binary, schema_dir)
        result = api.inspect_compatibility(binary, schema_dir=schema_dir)
    print(
        json.dumps(
            {
                "binary_path": str(binary.path),
                "binary_sha256": binary.sha256,
                "codex_version": binary.reported_version,
                "schema_evidence": "reused-retained-generation"
                if args.schema_dir
                else "fresh-native-generation",
                "semantic_schema_root_sha256": result.semantic_schema_root_sha256,
                "selected_callbacks": len(result.features.callbacks),
                "selected_notifications": len(result.features.notifications),
                "selected_requests": len(result.features.requests),
                "selected_transports": len(result.features.transports),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
