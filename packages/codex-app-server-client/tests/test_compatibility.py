from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from codex_app_server_client import (
    PINNED_PROTOCOL,
    AmbiguousCodexBinaryError,
    BinaryIdentity,
    CodexBinaryNotFoundError,
    CodexVersionError,
    RequestCapability,
    SchemaMalformedError,
    SchemaMissingError,
    SchemaRootMismatchError,
    UnsupportedFeatureError,
    inspect_compatibility,
    resolve_codex_binary,
)
from codex_app_server_client.compatibility import (
    _generate_schema_tree,
    _packaged_protocol_root,
    _required_features,
)


def fake_identity(version: str = "0.147.0") -> BinaryIdentity:
    return BinaryIdentity(
        path=Path("/nonexistent/codex"), reported_version=version, sha256="0" * 64
    )


def write_probe(directory: Path, version: str) -> Path:
    executable = directory / "codex"
    executable.write_text(f"#!{sys.executable}\nprint('codex-cli {version}')\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


class BinaryResolutionTests(unittest.TestCase):
    def test_explicit_binary_is_resolved_probed_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = write_probe(Path(temporary), "0.147.0")
            identity = resolve_codex_binary(executable)
            self.assertEqual(identity.path, executable.resolve())
            self.assertEqual(identity.reported_version, "0.147.0")
            self.assertEqual(len(identity.sha256), 64)

    def test_missing_explicit_binary_is_discriminating(self) -> None:
        with self.assertRaises(CodexBinaryNotFoundError):
            resolve_codex_binary("/definitely/missing/codex")

    def test_path_ambiguity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            write_probe(Path(first), "0.147.0")
            write_probe(Path(second), "0.147.0")
            with (
                mock.patch.dict(os.environ, {"PATH": os.pathsep.join((first, second))}),
                self.assertRaises(AmbiguousCodexBinaryError),
            ):
                resolve_codex_binary()

    def test_malformed_version_probe_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = write_probe(Path(temporary), "not-a-version")
            with self.assertRaises(CodexVersionError):
                resolve_codex_binary(executable)


class CompatibilityTests(unittest.TestCase):
    def test_retained_schema_is_accepted_without_process_side_effect(self) -> None:
        with mock.patch("subprocess.run") as run:
            result = inspect_compatibility(fake_identity())
        run.assert_not_called()
        self.assertEqual(result.target, PINNED_PROTOCOL)
        self.assertEqual(
            result.semantic_schema_root_sha256,
            "4e5c64213673b670d2575d7b7670d2089d49f92a92c56f2d16618e4a8857813e",
        )
        self.assertTrue(result.features.supports(RequestCapability.THREAD_START))

    def test_stale_version_is_rejected_before_schema_loading(self) -> None:
        with (
            mock.patch("importlib.resources.files") as files,
            self.assertRaises(CodexVersionError),
        ):
            inspect_compatibility(fake_identity("0.146.0"))
        files.assert_not_called()

    def test_changed_target_is_rejected(self) -> None:
        changed = type(PINNED_PROTOCOL)(
            codex_version=PINNED_PROTOCOL.codex_version,
            source_commit="f" * 40,
            schema_tree_root_sha256=PINNED_PROTOCOL.schema_tree_root_sha256,
            selected_surface_root_sha256=PINNED_PROTOCOL.selected_surface_root_sha256,
        )
        with self.assertRaises(SchemaRootMismatchError):
            inspect_compatibility(fake_identity(), changed)

    def test_missing_schema_root_is_rejected(self) -> None:
        with self.assertRaises(SchemaMissingError):
            inspect_compatibility(fake_identity(), schema_dir="/definitely/missing/schemas")

    def test_malformed_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            Path(temporary, "broken.json").write_text("{", encoding="utf-8")
            with self.assertRaises(SchemaMalformedError):
                inspect_compatibility(fake_identity(), schema_dir=temporary)

    def test_semantic_schema_drift_is_rejected(self) -> None:
        packaged = _packaged_protocol_root().joinpath("upstream", "0.147.0")
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "schemas"
            shutil.copytree(Path(str(packaged)), copied)
            request_id = copied / "RequestId.json"
            document = json.loads(request_id.read_text(encoding="utf-8"))
            document["description"] = "changed"
            request_id.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(SchemaRootMismatchError):
                inspect_compatibility(fake_identity(), schema_dir=copied)

    def test_missing_selected_feature_is_discriminating(self) -> None:
        upstream = _packaged_protocol_root().joinpath("upstream", "0.147.0")
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary)
            for name in (
                "codex_app_server_protocol.v2.schemas.json",
                "ServerRequest.json",
                "ClientNotification.json",
            ):
                Path(copied, name).write_bytes(upstream.joinpath(name).read_bytes())
            aggregate_path = copied / "codex_app_server_protocol.v2.schemas.json"
            aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
            aggregate["definitions"]["ClientRequest"]["oneOf"] = [
                variant
                for variant in aggregate["definitions"]["ClientRequest"]["oneOf"]
                if variant["properties"]["method"]["enum"] != ["thread/start"]
            ]
            aggregate_path.write_text(json.dumps(aggregate), encoding="utf-8")
            with self.assertRaises(UnsupportedFeatureError):
                _required_features(_packaged_protocol_root(), copied)

    def test_generation_uses_exact_nonexperimental_argv(self) -> None:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "schemas"
            with (
                mock.patch("subprocess.run", return_value=completed) as run,
                mock.patch(
                    "codex_app_server_client.compatibility._tree_roots",
                    return_value=("a", "b", 1, 1),
                ),
            ):
                _generate_schema_tree(fake_identity(), output)
        self.assertEqual(
            run.call_args.args[0][1:4],
            ["app-server", "generate-json-schema", "--out"],
        )
        self.assertNotIn("--experimental", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
