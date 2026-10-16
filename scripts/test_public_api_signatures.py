#!/usr/bin/env python3
"""Verify runtime API drift is rejected independently of fixture-byte checks."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from public_api_signatures import PROFILE_ROOTS, annotation_name, check_signatures, snapshot


class PublicApiSignatureTests(unittest.TestCase):
    def test_path_uses_public_name_across_interpreter_layouts(self) -> None:
        self.assertEqual(annotation_name(Path), "pathlib.Path")
        self.assertEqual(annotation_name(list[Path]), "builtins.list[pathlib.Path]")
        for internal_module in ("pathlib", "pathlib._local"):
            with patch.object(Path, "__module__", internal_module):
                self.assertEqual(annotation_name(Path), "pathlib.Path")

    def fixture(self, version: str) -> dict[str, object]:
        return json.loads((PROFILE_ROOTS[version] / "public-api.json").read_text())

    def test_both_profile_runtime_signatures_match(self) -> None:
        for version, root in PROFILE_ROOTS.items():
            with self.subTest(version=version):
                check_signatures(root, self.fixture(version))

    def test_untyped_lifecycle_replacement_is_rejected(self) -> None:
        for version, root in PROFILE_ROOTS.items():
            api = self.fixture(version)
            snapshot(api)
            module = importlib.import_module(api["root_module"])

            async def untyped(self, identity):
                raise AssertionError("signature inspection must never call this")

            with (
                self.subTest(version=version),
                patch.object(module.AppServerClient, "initialize", untyped),
                self.assertRaisesRegex(RuntimeError, "runtime public API signatures differ"),
            ):
                check_signatures(root, api)

    def test_unselected_export_is_rejected(self) -> None:
        api = self.fixture("0.162.1")
        snapshot(api)
        module = importlib.import_module(api["root_module"])
        with (
            patch.object(module, "__all__", [*module.__all__, "raw_call"]),
            self.assertRaisesRegex(RuntimeError, "runtime public exports differ"),
        ):
            snapshot(api)

    def test_modern_return_types_are_bound_to_the_modern_profile(self) -> None:
        record = snapshot(self.fixture("0.162.1"))
        callables = record["callables"]
        self.assertEqual(
            callables["AppServerClient.initialize"]["resolved_annotations"]["return"],
            "codex_app_server_client.v0_162_1.AppServerSession",
        )
        for name in ("events", "callbacks"):
            resolved = callables[f"AppServerSession.{name}"]["resolved_annotations"]["return"]
            self.assertIn("codex_app_server_client.v0_162_1.", resolved)
            self.assertNotIn("codex_app_server_client.models.", resolved)
            self.assertNotIn("codex_app_server_client.coordination.", resolved)
        for operation in self.fixture("0.162.1")["session_operations"]:
            annotations = callables[f"AppServerSession.{operation}"]["resolved_annotations"]
            for field in ("params", "return"):
                self.assertTrue(
                    annotations[field].startswith("codex_app_server_client.v0_162_1.models.")
                )


if __name__ == "__main__":
    unittest.main()
