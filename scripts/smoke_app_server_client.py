#!/usr/bin/env python3
"""Run one bounded package-local smoke against an explicit official Codex binary."""

from __future__ import annotations

import argparse
import asyncio
import json
import math

from codex_app_server_client import (
    AppServerClient,
    ClientIdentity,
    StdioTransport,
    ThreadListParams,
    inspect_compatibility,
    resolve_codex_binary,
)


async def smoke(codex: str, timeout: float) -> dict[str, object]:
    binary = resolve_codex_binary(codex)
    compatibility = inspect_compatibility(binary)
    client = await asyncio.wait_for(
        AppServerClient.connect(StdioTransport(binary), compatibility),
        timeout,
    )
    try:
        session = await asyncio.wait_for(
            client.initialize(ClientIdentity("utils-conformance", "0.1.0")),
            timeout,
        )
        threads = await session.list_threads(ThreadListParams(limit=1), timeout=timeout)
        return {
            "binary_path": str(binary.path),
            "binary_sha256": binary.sha256,
            "codex_version": binary.reported_version,
            "generation": session.generation,
            "listed_threads": len(threads.data),
            "semantic_schema_root_sha256": compatibility.semantic_schema_root_sha256,
            "selected_callbacks": len(compatibility.features.callbacks),
            "selected_notifications": len(compatibility.features.notifications),
            "selected_requests": len(compatibility.features.requests),
            "selected_transports": len(compatibility.features.transports),
        }
    finally:
        await asyncio.wait_for(client.close(), timeout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be positive and finite")
    print(json.dumps(asyncio.run(smoke(args.codex, args.timeout)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
