from __future__ import annotations

import asyncio
import inspect
import json
import re
import unittest
from pathlib import Path

import codex_app_server_client as client_api
from codex_app_server_client import (
    AppServerClient,
    ClientIdentity,
    InjectedTransport,
    StaleGenerationError,
    TransportOwnership,
    inspect_compatibility,
)
from fake_app_server import (
    CALLBACK_MATRIX,
    NOTIFICATION_MATRIX,
    DeterministicAppServer,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def compatibility():
    return inspect_compatibility(
        client_api.BinaryIdentity(
            path=Path("/nonexistent/codex"),
            reported_version="0.147.0",
            sha256="0" * 64,
        )
    )


class InstalledPublicConformanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_public_lifecycle_matrix(self) -> None:
        server = DeterministicAppServer()
        client = await AppServerClient.connect(
            InjectedTransport(server, ownership=TransportOwnership.OWNED),
            compatibility(),
        )
        session = await client.initialize(ClientIdentity("conformance", "0.1.0"))
        self.assertTrue(server.initialized)
        self.assertEqual(session.generation, 1)

        request_matrix = (
            ("start_thread", "ThreadStartParams", {}, "ThreadStartResponse"),
            (
                "resume_thread",
                "ThreadResumeParams",
                {"threadId": "thread-conformance"},
                "ThreadResumeResponse",
            ),
            (
                "read_thread",
                "ThreadReadParams",
                {"threadId": "thread-conformance"},
                "ThreadReadResponse",
            ),
            ("list_threads", "ThreadListParams", {}, "ThreadListResponse"),
            (
                "start_turn",
                "TurnStartParams",
                {"input": [], "threadId": "thread-conformance"},
                "TurnStartResponse",
            ),
            (
                "steer_turn",
                "TurnSteerParams",
                {
                    "expectedTurnId": "turn-conformance",
                    "input": [],
                    "threadId": "thread-conformance",
                },
                "TurnSteerResponse",
            ),
            (
                "interrupt_turn",
                "TurnInterruptParams",
                {"threadId": "thread-conformance", "turnId": "turn-conformance"},
                "TurnInterruptResponse",
            ),
            (
                "start_review",
                "ReviewStartParams",
                {"target": {"type": "uncommittedChanges"}, "threadId": "thread-conformance"},
                "ReviewStartResponse",
            ),
        )
        for operation, params_name, params, response_name in request_matrix:
            with self.subTest(operation=operation):
                typed_params = getattr(client_api, params_name).from_dict(params)
                result = await getattr(session, operation)(typed_params, timeout=1.0)
                self.assertIsInstance(result, getattr(client_api, response_name))
                if operation == "list_threads":
                    self.assertEqual(
                        dict(result.data[0].additional_properties),
                        {"canAcceptDirectInput": None, "historyMode": "full"},
                    )

        server.emit_notifications()
        events = session.events()
        projected = [await asyncio.wait_for(anext(events), 1.0) for _ in NOTIFICATION_MATRIX]
        self.assertEqual(
            [type(event).__name__ for event in projected],
            [model_name for _, _, model_name in NOTIFICATION_MATRIX],
        )
        await events.aclose()

        callbacks = session.callbacks()
        for index, (_, _, callback_name, response_name, response) in enumerate(CALLBACK_MATRIX):
            with self.subTest(callback=callback_name):
                request_id = server.emit_callback(index)
                callback = await asyncio.wait_for(anext(callbacks), 1.0)
                self.assertIsInstance(callback, getattr(client_api, callback_name))
                typed_response = getattr(client_api, response_name).from_dict(response)
                await callback.respond(typed_response)
                self.assertEqual(server.callback_results[-1]["id"], request_id)
                self.assertEqual(server.callback_results[-1]["result"], response)
        await callbacks.aclose()

        server.disconnect()
        await asyncio.wait_for(server.closed_event.wait(), 1.0)
        replacement_server = DeterministicAppServer()
        replacement = await client.replace(
            InjectedTransport(
                replacement_server,
                ownership=TransportOwnership.OWNED,
            )
        )
        self.assertEqual(replacement.generation, 2)
        with self.assertRaises(StaleGenerationError):
            await session.list_threads(client_api.ThreadListParams())
        listed = await replacement.list_threads(client_api.ThreadListParams(), timeout=1.0)
        self.assertEqual(len(listed.data), 1)
        await replacement.close()
        self.assertEqual(server.close_count, 1)
        self.assertEqual(replacement_server.close_count, 1)

    def test_installed_public_api_matches_frozen_fixture(self) -> None:
        fixture = json.loads(
            (PACKAGE_ROOT / "protocol" / "public-api.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(fixture["root_exports"]), set(client_api.__all__))
        self.assertEqual(len(client_api.__all__), 92)
        self.assertEqual(client_api.__version__, "0.1.0")
        self.assertEqual(
            str(inspect.signature(client_api.ClientLimits)),
            "(max_message_bytes: 'int' = 8388608, max_pending_calls: 'int' = 256, "
            "max_events: 'int' = 1024, max_callbacks: 'int' = 64, "
            "max_backoff_seconds: 'float' = 30.0) -> None",
        )
        self.assertFalse(hasattr(client_api, "RpcEngine"))
        self.assertFalse(hasattr(client_api.AppServerSession, "call_raw"))

    def test_public_readme_examples_execute(self) -> None:
        readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
        examples = re.findall(r"```python executable\n(.*?)```", readme, flags=re.DOTALL)
        self.assertTrue(examples)
        for example in examples:
            namespace = {"__name__": "__docs_example__"}
            exec(compile(example, "README.md", "exec"), namespace)


if __name__ == "__main__":
    unittest.main()
