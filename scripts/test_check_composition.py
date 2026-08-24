#!/usr/bin/env python3
"""Negative tests for the frozen neutral composition runner."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import check_composition


def exact_fixture_prefix() -> str:
    imports = "\n".join(check_composition.EXPECTED_IMPORT_STATEMENTS) + "\n"
    accesses = "\n".join(
        f"{check_composition.PACKAGE_IMPORT_ALIASES[module]}.{attribute}"
        for module in sorted(check_composition.PUBLIC_MODULE_ATTRIBUTES)
        for attribute in sorted(check_composition.PUBLIC_MODULE_ATTRIBUTES[module])
    )
    return imports + accesses + "\n"


def packages() -> dict[str, dict[str, object]]:
    return {
        name: {
            "path": f"packages/{name}",
            "import": name.replace("-", "_"),
            "version": "0.1.0",
            "runtime_dependencies": (),
        }
        for name in (
            "codex-app-server-client",
            "embedded-service-contract",
            "runtime-manifest",
        )
    }


def contract() -> dict[str, object]:
    value = {
        "schema_version": 1,
        "fixture_sha256": hashlib.sha256(check_composition.FIXTURE_PATH.read_bytes()).hexdigest(),
        "manifest_sha256": "0" * 64,
        "packages": {
            name: {
                "version": "0.1.0",
                "wheel_sha256": wheel * 64,
                "wheel_content_root_sha256": content * 64,
            }
            for name, wheel, content in (
                ("codex-app-server-client", "a", "b"),
                ("embedded-service-contract", "c", "d"),
                ("runtime-manifest", "e", "f"),
            )
        },
        "protocol": {
            "version": "0.147.0",
            "schema_root_sha256": "1" * 64,
            "selected_surface_root_sha256": "2" * 64,
        },
    }
    value["manifest_sha256"] = check_composition.canonical_manifest_sha256(value)
    return value


class CompositionAuditTests(unittest.TestCase):
    def test_contract_requires_exact_packages_versions_roots_and_fields(self) -> None:
        mutations = []
        missing = contract()
        del missing["packages"]["embedded-service-contract"]
        mutations.append(missing)
        version = contract()
        version["packages"]["codex-app-server-client"]["version"] = "2"
        mutations.append(version)
        root = contract()
        root["packages"]["runtime-manifest"]["wheel_sha256"] = "A" * 64
        mutations.append(root)
        hidden = contract()
        hidden["protocol"]["authority"] = True
        mutations.append(hidden)
        boolean_schema = contract()
        boolean_schema["schema_version"] = True
        mutations.append(boolean_schema)
        changed_manifest = contract()
        changed_manifest["manifest_sha256"] = "0" * 64
        mutations.append(changed_manifest)
        changed_fixture = contract()
        changed_fixture["fixture_sha256"] = "0" * 64
        mutations.append(changed_fixture)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                check_composition.validate_contract(value, packages())
        check_composition.validate_contract(contract(), packages())

    def test_fixture_imports_reject_private_external_and_incomplete_surfaces(self) -> None:
        check_composition.validate_fixture_imports(check_composition.FIXTURE_PATH)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.py"
            for source in (
                "import codex_app_server_client.compatibility\n",
                "import third_party\n",
                "import codex_app_server_client\n",
                "import subprocess\n",
                "import socket\n",
            ):
                with self.subTest(source=source):
                    path.write_text(source, encoding="utf-8")
                    with self.assertRaises(RuntimeError):
                        check_composition.validate_fixture_imports(path)

            exact_prefix = exact_fixture_prefix()
            path.write_text(exact_prefix + "client_api.compatibility\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "non-public package attribute"):
                check_composition.validate_fixture_imports(path)
            path.write_text(
                exact_prefix
                + "import importlib\n"
                + "importlib.import_module('codex_app_server_client.compatibility')\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "import statements or aliases"):
                check_composition.validate_fixture_imports(path)
            path.write_text(
                exact_prefix + "getattr(client_api, '_private', None)\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "package module object escape"):
                check_composition.validate_fixture_imports(path)

            bypasses = {
                "alias_attr": "alias = client_api\nalias.compatibility\n",
                "alias_getattr": "alias = client_api\ngetattr(alias, '_private', None)\n",
                "nested_attr": "client_api.AppServerClient._private\n",
                "eval_import": "eval('__import__(\"codex_app_server_client.compatibility\")')\n",
                "sys_modules": (
                    "from sys import modules\nmodules['codex_app_server_client.compatibility']\n"
                ),
                "bare_eval": "eval('1')\n",
            }
            for name, source in bypasses.items():
                with self.subTest(name=name):
                    path.write_text(exact_prefix + source, encoding="utf-8")
                    with self.assertRaises(RuntimeError):
                        check_composition.validate_fixture_imports(path)

            path.write_text(
                exact_prefix.replace(
                    "import codex_app_server_client as client_api",
                    "import codex_app_server_client as renamed_client",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "import statements or aliases"):
                check_composition.validate_fixture_imports(path)

    def test_artifact_bytes_and_content_root_are_independent_exact_inputs(self) -> None:
        expected = contract()["packages"]["codex-app-server-client"]
        check_composition.verify_artifact(
            "codex-app-server-client",
            wheel_sha256="a" * 64,
            content_root_sha256="b" * 64,
            expected=expected,
        )
        with self.assertRaisesRegex(RuntimeError, "wheel bytes differ"):
            check_composition.verify_artifact(
                "codex-app-server-client",
                wheel_sha256="0" * 64,
                content_root_sha256="b" * 64,
                expected=expected,
            )
        with self.assertRaisesRegex(RuntimeError, "content root differs"):
            check_composition.verify_artifact(
                "codex-app-server-client",
                wheel_sha256="a" * 64,
                content_root_sha256="0" * 64,
                expected=expected,
            )

    def test_result_rejects_hidden_fields_and_root_or_scenario_drift(self) -> None:
        full_contract = contract()
        embedded = full_contract["packages"]["embedded-service-contract"]
        protocol = full_contract["protocol"]
        result = {
            "client": {
                "channel_close_count": 1,
                "generation": 1,
                "listed_threads": 0,
                "transport": "injected-byte-channel",
            },
            "incompatible_root_diagnostics": [
                {
                    "expected": f"sha256:{embedded['wheel_content_root_sha256']}",
                    "kind": "dependency-root",
                    "observed": f"sha256:{'0' * 64}",
                    "subject": "embedded-service-contract",
                },
                {
                    "expected": f"sha256:{protocol['selected_surface_root_sha256']}",
                    "kind": "protocol-schema",
                    "observed": f"sha256:{'0' * 64}",
                    "subject": "codex-app-server-surface",
                },
            ],
            "lifecycle": {
                "embedded": {"events": 6, "scenarios": 3, "shape": "embedded"},
                "process_owner_count": 1,
                "service": {"events": 6, "scenarios": 3, "shape": "service"},
            },
            "manifest_compatible": True,
            "manifest_sha256": full_contract["manifest_sha256"],
            "packages": {
                name: record["version"] for name, record in full_contract["packages"].items()
            },
            "protocol": full_contract["protocol"],
            "public_modules": sorted(check_composition.PACKAGE_MODULES),
            "schema_version": 1,
        }
        check_composition.validate_result(result, full_contract)
        for mutation in (
            "hidden",
            "protocol",
            "owner",
            "boolean-schema",
            "duplicate-diagnostic",
            "hidden-capability",
        ):
            changed = copy.deepcopy(result)
            if mutation == "hidden":
                changed["authority"] = "approved"
            elif mutation == "protocol":
                changed["protocol"]["schema_root_sha256"] = "0" * 64
            elif mutation == "owner":
                changed["lifecycle"]["process_owner_count"] = 2
            elif mutation == "boolean-schema":
                changed["schema_version"] = True
            elif mutation == "duplicate-diagnostic":
                changed["incompatible_root_diagnostics"].append(
                    changed["incompatible_root_diagnostics"][0]
                )
            else:
                document = json.loads(check_composition.canonical_manifest_document(full_contract))
                document["capabilities"].append({"name": "implicit-authority", "version": "1"})
                payload = (
                    json.dumps(
                        document,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    + "\n"
                )
                changed["manifest_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                check_composition.validate_result(changed, full_contract)


if __name__ == "__main__":
    unittest.main()
