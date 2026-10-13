"""Two exact profiles share lifecycle machinery without sharing model state."""

from __future__ import annotations

import asyncio
import json
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import codex_app_server_client as legacy
from codex_app_server_client import v0_162_1 as current
from codex_app_server_client.compatibility import _protocol_root_for
from test_session import ScriptedSessionPeer, minimum_value

OPERATIONS = (
    ("start_thread", "thread/start", "ThreadStartParams", "ThreadStartResponse"),
    ("resume_thread", "thread/resume", "ThreadResumeParams", "ThreadResumeResponse"),
    ("read_thread", "thread/read", "ThreadReadParams", "ThreadReadResponse"),
    ("list_threads", "thread/list", "ThreadListParams", "ThreadListResponse"),
    ("start_turn", "turn/start", "TurnStartParams", "TurnStartResponse"),
    ("steer_turn", "turn/steer", "TurnSteerParams", "TurnSteerResponse"),
    ("interrupt_turn", "turn/interrupt", "TurnInterruptParams", "TurnInterruptResponse"),
    ("start_review", "review/start", "ReviewStartParams", "ReviewStartResponse"),
)


def identity(api):
    return api.BinaryIdentity(
        Path("/never-executed-codex"), api.PINNED_PROTOCOL.codex_version, "0" * 64
    )


def fixture(api, name):
    root = _protocol_root_for(api.PINNED_PROTOCOL).joinpath(
        "upstream", api.PINNED_PROTOCOL.codex_version
    )
    path = root.joinpath("v2", name + ".json")
    if not path.is_file():
        path = root.joinpath(name + ".json")
    schema = json.loads(path.read_text())
    return minimum_value(schema, schema)


def peer_for(api):
    peer = ScriptedSessionPeer()
    peer.responses = {method: fixture(api, response) for _, method, _, response in OPERATIONS}
    return peer


class VersionedSessionTests(unittest.IsolatedAsyncioTestCase):
    async def initialize(self, api, peer=None):
        peer = peer_for(api) if peer is None else peer
        client = await api.AppServerClient.connect(
            api.InjectedTransport(peer, ownership=api.TransportOwnership.OWNED),
            api.inspect_compatibility(identity(api)),
        )
        self.addAsyncCleanup(client.close)
        session = await client.initialize(api.ClientIdentity("fixture", "1"))
        return peer, client, session

    async def test_two_profiles_all_eight_operations_keep_exact_models(self):
        old_type = legacy.ThreadReadParams
        pairs = [await self.initialize(api) for api in (legacy, current)]
        for api, (peer, _, session) in zip((legacy, current), pairs, strict=True):
            for operation, method, params_name, response_name in OPERATIONS:
                with self.subTest(version=api.PINNED_PROTOCOL.codex_version, method=method):
                    params = getattr(api, params_name).from_dict(fixture(api, params_name))
                    result = await getattr(session, operation)(params)
                    self.assertIs(type(result), getattr(api, response_name))
                    self.assertEqual(peer.writes[-1]["params"], params.to_dict())
            self.assertIs(type(session), api.AppServerSession)
            opted_out = peer.writes[0]["params"]["capabilities"]["optOutNotificationMethods"]
            self.assertEqual(len(opted_out), 55 if api is legacy else 69)
        self.assertIs(legacy.ThreadReadParams, old_type)
        self.assertEqual(legacy.PINNED_PROTOCOL.codex_version, "0.147.0")
        self.assertNotIn("projectId", pairs[0][0].responses["thread/read"]["thread"])
        self.assertIn("projectId", pairs[1][0].responses["thread/read"]["thread"])

    async def test_cross_profile_params_and_identity_reject_before_write(self):
        for api, foreign in ((legacy, current), (current, legacy)):
            peer = peer_for(api)
            client = await api.AppServerClient.connect(
                api.InjectedTransport(peer, ownership=api.TransportOwnership.OWNED),
                api.inspect_compatibility(identity(api)),
            )
            self.addAsyncCleanup(client.close)
            with self.assertRaises(TypeError):
                await client.initialize(foreign.ClientIdentity("foreign", "1"))
            self.assertEqual(peer.writes, [])
            session = await client.initialize(api.ClientIdentity("local", "1"))
            with self.assertRaises(TypeError):
                await session.read_thread(foreign.ThreadReadParams(threadId="x"))
            self.assertEqual(len(peer.writes), 2)

    async def test_legacy_identity_subclass_remains_supported(self):
        class Identity(legacy.ClientIdentity):
            pass

        peer = peer_for(legacy)
        client = await legacy.AppServerClient.connect(
            legacy.InjectedTransport(peer, ownership=legacy.TransportOwnership.OWNED),
            legacy.inspect_compatibility(identity(legacy)),
        )
        self.addAsyncCleanup(client.close)
        await client.initialize(Identity("fixture", "1"))
        self.assertEqual(peer.writes[0]["params"]["clientInfo"]["name"], "fixture")

    async def test_mismatched_compatibility_and_stdio_profiles_never_open(self):
        for api, foreign in ((legacy, current), (current, legacy)):
            peer = peer_for(api)
            transport = api.InjectedTransport(peer, ownership=api.TransportOwnership.OWNED)
            with self.assertRaises(api.UnsupportedFeatureError):
                await api.AppServerClient.connect(
                    transport, foreign.inspect_compatibility(identity(foreign))
                )
            self.assertEqual(peer.writes, [])
            self.assertEqual(peer.close_count, 0)
            stdio = foreign.StdioTransport(identity(foreign))
            with (
                patch.object(stdio, "_open_channel", side_effect=AssertionError("must not open")),
                self.assertRaises(api.UnsupportedFeatureError),
            ):
                await api.AppServerClient.connect(stdio, api.inspect_compatibility(identity(api)))
        with self.assertRaises(legacy.CodexVersionError):
            legacy.inspect_compatibility(identity(current))
        with self.assertRaises(current.SchemaRootMismatchError):
            current.inspect_compatibility(identity(legacy), target=legacy.PINNED_PROTOCOL)
        forged = replace(current.PINNED_PROTOCOL, codex_version="0.162.2")
        with self.assertRaises(legacy.SchemaRootMismatchError):
            legacy.inspect_compatibility(
                replace(identity(current), reported_version="0.162.2"), target=forged
            )

    async def test_new_callbacks_events_and_replacement_retain_profile(self):
        peer, client, session = await self.initialize(current)
        peer._queue_notification({"method": "warning", "params": {"message": "fixture"}})
        event = await asyncio.wait_for(anext(session.events()), 1)
        self.assertIs(type(event), current.WarningNotification)
        specs = (
            (
                "item/commandExecution/requestApproval",
                "CommandExecutionRequestApprovalParams",
                "CommandExecutionRequestApprovalResponse",
                "CommandExecutionApprovalCallback",
            ),
            (
                "item/fileChange/requestApproval",
                "FileChangeRequestApprovalParams",
                "FileChangeRequestApprovalResponse",
                "FileChangeApprovalCallback",
            ),
            (
                "item/tool/requestUserInput",
                "ToolRequestUserInputParams",
                "ToolRequestUserInputResponse",
                "UserInputCallback",
            ),
        )
        for i, (method, params, response, callback_name) in enumerate(specs):
            value = fixture(current, params)
            if method == "item/commandExecution/requestApproval":
                value["kind"] = "writeStdin"
            peer.queue_callback(i, method, value)
            callback = await asyncio.wait_for(anext(session.callbacks()), 1)
            self.assertIs(type(callback), getattr(current, callback_name))
            with self.assertRaises(TypeError):
                await callback.respond(
                    getattr(legacy, response).from_dict(fixture(legacy, response))
                )
            await callback.respond(getattr(current, response).from_dict(fixture(current, response)))
            with self.assertRaises(current.CallCancelledError):
                await callback.respond(
                    getattr(current, response).from_dict(fixture(current, response))
                )
        peer.queue_callback("stale", specs[0][0], fixture(current, specs[0][1]))
        stale = await asyncio.wait_for(anext(session.callbacks()), 1)
        peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1)
        next_peer = peer_for(current)
        replacement = await client.replace(
            current.InjectedTransport(next_peer, ownership=current.TransportOwnership.OWNED)
        )
        self.assertIs(type(replacement), current.AppServerSession)
        self.assertEqual(replacement.generation, 2)
        result = await replacement.read_thread(current.ThreadReadParams(threadId="x"))
        self.assertIs(type(result), current.ThreadReadResponse)
        with self.assertRaises(current.StaleGenerationError):
            await stale.respond(current.CommandExecutionRequestApprovalResponse(decision="cancel"))
        self.assertEqual(peer.close_count, 1)

    async def test_new_unselected_notification_is_terminal(self):
        peer, client, session = await self.initialize(current)
        peer._queue_notification({"method": "thread/realtime/itemAdded", "params": {}})
        await asyncio.wait_for(client._engine.wait_closed(), 1)
        with self.assertRaises(current.SessionStateError):
            await session.read_thread(current.ThreadReadParams(threadId="x"))
        self.assertEqual(peer.close_count, 1)

    def test_bindings_are_immutable_snapshots(self):
        for api in (legacy, current):
            binding = api.AppServerClient._binding()
            with self.assertRaises(TypeError):
                binding.models["ClientIdentity"] = object
            with self.assertRaises(TypeError):
                binding.notification_types["new"] = object


if __name__ == "__main__":
    unittest.main()
