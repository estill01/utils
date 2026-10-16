from __future__ import annotations

import asyncio
import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import codex_app_server_client as api
from test_session import ScriptedSessionPeer, fake_identity

THREAD_ID = "019ad010-41b2-7000-8d70-809573c9d334"
NOT_LOADED = f"thread not loaded: {THREAD_ID}"


class SessionMetadataTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compatibility = api.inspect_compatibility(fake_identity())

    async def connect(self, peer: ScriptedSessionPeer) -> api.AppServerClient:
        client = await api.AppServerClient.connect(
            api.InjectedTransport(peer, ownership=api.TransportOwnership.OWNED),
            self.compatibility,
        )
        self.addAsyncCleanup(client.close)
        return client

    async def test_initialize_info_is_selected_validated_and_immutable(self) -> None:
        peer = ScriptedSessionPeer()
        peer.initialize_result["unrestrictedExtra"] = {"private": ["not-public"]}
        client = await self.connect(peer)
        session = await client.initialize(api.ClientIdentity("metadata-fixture", "1"))
        info = session.initialize_info
        self.assertEqual(info, api.InitializeInfo("/tmp/codex-home", "fixture", "unix", "macos"))
        self.assertEqual(
            [field.name for field in fields(info)],
            ["codex_home", "user_agent", "platform_family", "platform_os"],
        )
        self.assertIs(session.initialize_info, info)
        self.assertFalse(hasattr(info, "__dict__"))
        self.assertFalse(hasattr(info, "additional_properties"))
        self.assertFalse(hasattr(info, "to_dict"))
        self.assertNotIn("not-public", repr(info))
        with self.assertRaises(FrozenInstanceError):
            info.codex_home = "/changed"  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            session.initialize_info = info  # type: ignore[misc]
        peer.initialize_result["codexHome"] = "/peer-mutated"
        self.assertEqual(info.codex_home, "/tmp/codex-home")
        await session.close()
        self.assertIs(session.initialize_info, info)

    async def test_initialize_requires_every_typed_field_before_exposing_session(self) -> None:
        for field in ("codexHome", "userAgent", "platformFamily", "platformOs"):
            for invalid in ("missing", None, [], 1, True):
                with self.subTest(field=field, invalid=invalid):
                    peer = ScriptedSessionPeer()
                    if invalid == "missing":
                        del peer.initialize_result[field]
                    else:
                        peer.initialize_result[field] = invalid
                    client = await self.connect(peer)
                    with self.assertRaises(api.InitializationError):
                        await client.initialize(api.ClientIdentity("metadata-fixture", "1"))
                    self.assertIsNone(client._session)
                    self.assertEqual([write["method"] for write in peer.writes], ["initialize"])
                    self.assertEqual(peer.close_count, 1)

    async def test_replace_refreshes_metadata_and_preserves_retired_snapshot(self) -> None:
        old_peer = ScriptedSessionPeer()
        client = await self.connect(old_peer)
        old_session = await client.initialize(api.ClientIdentity("metadata-fixture", "1"))
        old_info = old_session.initialize_info
        old_peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        new_peer = ScriptedSessionPeer()
        new_peer.initialize_result = {
            "codexHome": "/replacement/home",
            "userAgent": "replacement-fixture",
            "platformFamily": "windows",
            "platformOs": "windows",
        }
        new_session = await client.replace(
            api.InjectedTransport(new_peer, ownership=api.TransportOwnership.OWNED)
        )
        self.assertEqual(new_session.generation, 2)
        self.assertEqual(
            new_session.initialize_info,
            api.InitializeInfo("/replacement/home", "replacement-fixture", "windows", "windows"),
        )
        self.assertIs(old_session.initialize_info, old_info)
        self.assertNotEqual(new_session.initialize_info, old_info)
        with self.assertRaises(api.StaleGenerationError):
            await old_session.list_threads(api.ThreadListParams())
        await new_session.list_threads(api.ThreadListParams())

    async def test_invalid_replacement_does_not_publish_old_or_partial_metadata(self) -> None:
        peer = ScriptedSessionPeer()
        client = await self.connect(peer)
        old_session = await client.initialize(api.ClientIdentity("metadata-fixture", "1"))
        peer.disconnect()
        await asyncio.wait_for(client._engine.wait_closed(), 1.0)
        replacement = ScriptedSessionPeer()
        replacement.initialize_result["codexHome"] = []
        with self.assertRaises(api.RestartError):
            await client.replace(
                api.InjectedTransport(replacement, ownership=api.TransportOwnership.OWNED)
            )
        self.assertIsNone(client._session)
        self.assertEqual(old_session.initialize_info.codex_home, "/tmp/codex-home")
        self.assertEqual(replacement.close_count, 1)

    async def test_exact_thread_not_loaded_rejection_is_content_free_and_recoverable(self) -> None:
        peer = ScriptedSessionPeer()
        peer.error_overrides["thread/read"] = {"code": -32600, "message": NOT_LOADED}
        client = await self.connect(peer)
        session = await client.initialize(api.ClientIdentity("metadata-fixture", "1"))
        with self.assertRaises(api.RemoteRpcError) as raised:
            await session.read_thread(api.ThreadReadParams(threadId=THREAD_ID))
        error = raised.exception
        self.assertIs(error.category, api.RemoteRpcErrorCategory.THREAD_NOT_LOADED)
        self.assertEqual(set(vars(error)), {"request_id", "code", "has_data", "category"})
        self.assertFalse(error.has_data)
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn(THREAD_ID, repr(error))
        self.assertNotIn(NOT_LOADED, repr(vars(error)))
        del peer.error_overrides["thread/read"]
        await session.read_thread(api.ThreadReadParams(threadId=THREAD_ID))
        self.assertIsNone(client._engine.failure)
        self.assertEqual(client._engine.pending_count, 0)

    async def test_ambiguous_rejections_remain_unknown_without_retaining_content(self) -> None:
        variants = [
            {"code": -32601, "message": NOT_LOADED},
            {"code": -32603, "message": NOT_LOADED},
            {"code": -32600, "message": NOT_LOADED, "data": None},
            {"code": -32600, "message": NOT_LOADED, "data": {"secret": "private-data"}},
        ]
        variants += [
            {"code": -32600, "message": message}
            for message in (
                "thread not loaded",
                "thread not loaded: arbitrary-id",
                NOT_LOADED + "\n",
                NOT_LOADED + " extra",
                "prefix " + NOT_LOADED,
                NOT_LOADED.replace(THREAD_ID, THREAD_ID.upper()),
                NOT_LOADED.replace(THREAD_ID, "{" + THREAD_ID + "}"),
                NOT_LOADED.replace(THREAD_ID, THREAD_ID.replace("-", "")),
                NOT_LOADED.replace(THREAD_ID, "g" + THREAD_ID[1:]),
                "Thread not loaded: " + THREAD_ID,
                "thread not loaded:  " + THREAD_ID,
                "unrelated private-message",
            )
        ]
        peer = ScriptedSessionPeer()
        client = await self.connect(peer)
        session = await client.initialize(api.ClientIdentity("metadata-fixture", "1"))
        for remote in variants:
            with self.subTest(remote=remote):
                peer.error_overrides["thread/read"] = remote
                with self.assertRaises(api.RemoteRpcError) as raised:
                    await session.read_thread(api.ThreadReadParams(threadId=THREAD_ID))
                error = raised.exception
                self.assertIs(error.category, api.RemoteRpcErrorCategory.UNKNOWN)
                self.assertEqual(error.has_data, "data" in remote)
                self.assertEqual(set(vars(error)), {"request_id", "code", "has_data", "category"})
                self.assertNotIn(THREAD_ID, repr(error))
                self.assertNotIn("private-", repr(error) + repr(vars(error)))
        self.assertIsNone(client._engine.failure)

    async def test_known_message_on_other_operation_remains_unknown(self) -> None:
        peer = ScriptedSessionPeer()
        peer.error_overrides["thread/resume"] = {"code": -32600, "message": NOT_LOADED}
        client = await self.connect(peer)
        session = await client.initialize(api.ClientIdentity("metadata-fixture", "1"))
        with self.assertRaises(api.RemoteRpcError) as raised:
            await session.resume_thread(api.ThreadResumeParams(threadId=THREAD_ID))
        self.assertIs(raised.exception.category, api.RemoteRpcErrorCategory.UNKNOWN)


class MetadataContractTests(unittest.TestCase):
    def test_values_reject_mutable_fields_and_untyped_categories(self) -> None:
        info = api.InitializeInfo("/fixture/home", "fixture", "unix", "linux")
        for field in fields(info):
            with self.subTest(field=field.name), self.assertRaises(TypeError):
                replace(info, **{field.name: []})
        error = api.RemoteRpcError(request_id=1, code=-32600, has_data=False)
        self.assertIs(error.category, api.RemoteRpcErrorCategory.UNKNOWN)
        with self.assertRaises(TypeError):
            api.RemoteRpcError(request_id=1, code=-32600, has_data=False, category="unknown")
        self.assertEqual(
            {item.value for item in api.RemoteRpcErrorCategory}, {"unknown", "thread-not-loaded"}
        )

    def test_manifest_version_and_root_exports_match(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest_bytes = (root / "protocol/public-api.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        compatibility = json.loads((root / "protocol/compatibility.json").read_bytes())
        self.assertEqual(set(manifest["root_exports"]), set(api.__all__))
        self.assertEqual(api.__version__, "0.4.1")
        self.assertEqual(api.PINNED_PROTOCOL.codex_version, "0.147.0")
        self.assertEqual(
            hashlib.sha256(manifest_bytes).hexdigest(), compatibility["public_api_sha256"]
        )
        self.assertEqual(
            manifest["lifecycle"]["AppServerSession.initialize_info"],
            "property -> InitializeInfo",
        )
        self.assertEqual(
            manifest["errors"]["categories"]["RemoteRpcErrorCategory"],
            {item.name: item.value for item in api.RemoteRpcErrorCategory},
        )


if __name__ == "__main__":
    unittest.main()
