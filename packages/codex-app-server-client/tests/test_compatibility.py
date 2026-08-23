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


def write_mutating_probe(directory: Path, action: str) -> Path:
    executable = directory / "codex"
    executable.write_text(
        (
            f"#!{sys.executable}\n"
            "from pathlib import Path\n"
            "target = Path(__file__)\n"
            + (
                "target.unlink()\n"
                if action == "delete"
                else "target.write_text('# replacement\\n', encoding='utf-8')\n"
            )
            + "print('codex-cli 0.147.0')\n"
        ),
        encoding="utf-8",
    )
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

    def test_explicit_dot_slash_path_does_not_search_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_probe(directory, "0.147.0")
            previous = Path.cwd()
            try:
                os.chdir(directory)
                with mock.patch.dict(os.environ, {"PATH": "/definitely/missing"}):
                    identity = resolve_codex_binary("./codex")
            finally:
                os.chdir(previous)
        self.assertEqual(identity.reported_version, "0.147.0")

    def test_pathlike_bare_filename_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_probe(directory, "0.147.0")
            previous = Path.cwd()
            try:
                os.chdir(directory)
                with mock.patch.dict(os.environ, {"PATH": "/definitely/missing"}):
                    identity = resolve_codex_binary(Path("codex"))
            finally:
                os.chdir(previous)
        self.assertEqual(identity.reported_version, "0.147.0")

    def test_self_replacing_probe_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = write_mutating_probe(Path(temporary), "replace")
            with self.assertRaises(CodexVersionError):
                resolve_codex_binary(executable)

    def test_self_deleting_probe_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = write_mutating_probe(Path(temporary), "delete")
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
            copied = Path(temporary) / "schemas"
            packaged = _packaged_protocol_root().joinpath("upstream", "0.147.0")
            shutil.copytree(Path(str(packaged)), copied)
            Path(copied, "RequestId.json").write_text("{", encoding="utf-8")
            with self.assertRaises(SchemaMalformedError):
                inspect_compatibility(fake_identity(), schema_dir=copied)

    def test_missing_required_schema_is_discriminating_through_public_api(self) -> None:
        packaged = _packaged_protocol_root().joinpath("upstream", "0.147.0")
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "schemas"
            shutil.copytree(Path(str(packaged)), copied)
            (copied / "ClientNotification.json").unlink()
            with self.assertRaises(SchemaMissingError):
                inspect_compatibility(fake_identity(), schema_dir=copied)

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

    def test_missing_selected_feature_is_discriminating_through_public_api(self) -> None:
        upstream = _packaged_protocol_root().joinpath("upstream", "0.147.0")
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "schemas"
            shutil.copytree(Path(str(upstream)), copied)
            aggregate_path = copied / "codex_app_server_protocol.v2.schemas.json"
            aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
            aggregate["definitions"]["ClientRequest"]["oneOf"] = [
                variant
                for variant in aggregate["definitions"]["ClientRequest"]["oneOf"]
                if variant["properties"]["method"]["enum"] != ["thread/start"]
            ]
            aggregate_path.write_text(json.dumps(aggregate), encoding="utf-8")
            with self.assertRaises(UnsupportedFeatureError):
                inspect_compatibility(fake_identity(), schema_dir=copied)

    def test_changed_selected_surface_is_rejected_through_public_api(self) -> None:
        packaged = _packaged_protocol_root()
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "protocol"
            shutil.copytree(Path(str(packaged)), copied)
            surface_path = copied / "supported-surface.json"
            surface = json.loads(surface_path.read_text(encoding="utf-8"))
            surface["client_requests"]["public_typed"].remove("review/start")
            surface_path.write_text(json.dumps(surface), encoding="utf-8")
            with (
                mock.patch(
                    "codex_app_server_client.compatibility._packaged_protocol_root",
                    return_value=copied,
                ),
                self.assertRaises(SchemaRootMismatchError),
            ):
                inspect_compatibility(fake_identity())

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
