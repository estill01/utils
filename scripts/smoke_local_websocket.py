#!/usr/bin/env python3
"""No-model 0.156.1 smoke with a disposable, credential-free daemon and home."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path

from codex_app_server_client import v0_156_1 as api


async def smoke(executable: str) -> dict[str, object]:
    binary = api.resolve_codex_binary(executable)
    compatibility = api.inspect_compatibility(binary)
    with tempfile.TemporaryDirectory(prefix="native156-") as temporary:
        root = Path(temporary)
        home = root / "home"
        home.mkdir(mode=0o700)
        socket = root / "control.sock"
        process = await asyncio.create_subprocess_exec(
            str(binary.path),
            "app-server",
            "--listen",
            f"unix://{socket}",
            env={**os.environ, "CODEX_HOME": str(home)},
            cwd=root,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        client = None
        try:
            async with asyncio.timeout(15):
                while not socket.exists():
                    if process.returncode is not None:
                        raise RuntimeError("isolated app-server exited before its socket appeared")
                    await asyncio.sleep(0.05)
                client = await api.AppServerClient.connect(
                    api.LocalWebSocketTransport(socket), compatibility
                )
                session = await client.initialize(api.ClientIdentity("utils-local-smoke", "0.4.0"))
                listed = await session.list_threads(api.ThreadListParams(limit=1), timeout=5)
                started = await session.start_thread(
                    api.ThreadStartParams(cwd=str(root)), timeout=5
                )
                try:
                    await session.list_turns(
                        api.ThreadTurnsListParams(
                            threadId=started.thread.id, limit=1, itemsView="full"
                        ),
                        timeout=5,
                    )
                except api.RemoteRpcError as error:
                    if error.code != -32600:
                        raise
                    history_error = error.code
                else:
                    raise RuntimeError("unmaterialized native thread unexpectedly has history")
                await client.close()
                client = None
                assert process.returncode is None
                return {
                    "codex_version": binary.reported_version,
                    "binary_sha256": binary.sha256,
                    "semantic_schema_root_sha256": compatibility.semantic_schema_root_sha256,
                    "transport": "local-websocket",
                    "isolated_home": True,
                    "credentials_copied": False,
                    "listed_threads": len(listed.data),
                    "turn_history_request_error_code": history_error,
                    "successful_native_turn_page": False,
                    "model_turns_started": 0,
                    "daemon_alive_after_client_close": True,
                }
        finally:
            try:
                if client is not None:
                    await asyncio.wait_for(client.close(), 5)
            finally:
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), 5)
                    except TimeoutError:
                        process.kill()
                        await asyncio.wait_for(process.wait(), 5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(smoke(args.codex)), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
