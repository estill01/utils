#!/usr/bin/env python3
"""Run one bounded official-binary schema currentness check."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from codex_app_server_client import inspect_compatibility, resolve_codex_binary
from codex_app_server_client.compatibility import _generate_schema_tree


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", required=True)
    args = parser.parse_args()
    binary = resolve_codex_binary(args.codex)
    with tempfile.TemporaryDirectory(prefix="utils-codex-schema-currentness-") as temporary:
        schema_dir = Path(temporary) / "schema"
        _generate_schema_tree(binary, schema_dir)
        result = inspect_compatibility(binary, schema_dir=schema_dir)
    print(
        json.dumps(
            {
                "binary_path": str(binary.path),
                "binary_sha256": binary.sha256,
                "codex_version": binary.reported_version,
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
