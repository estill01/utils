#!/usr/bin/env python3
"""Negative tests for the frozen neutral composition runner."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import check_composition


def packages() -> dict[str, dict[str, object]]:
    return {
        "alpha": {
            "path": "packages/alpha",
            "import": "alpha",
            "version": "1",
            "runtime_dependencies": (),
        }
    }


def contract() -> dict[str, object]:
    return {
        "schema_version": 1,
        "packages": {
            "alpha": {
                "version": "1",
                "wheel_sha256": "a" * 64,
                "wheel_content_root_sha256": "b" * 64,
            }
        },
        "protocol": {
            "version": "1",
            "schema_root_sha256": "c" * 64,
            "selected_surface_root_sha256": "d" * 64,
        },
    }


class CompositionAuditTests(unittest.TestCase):
    def test_contract_requires_exact_packages_versions_roots_and_fields(self) -> None:
        mutations = []
        missing = contract()
        del missing["packages"]["alpha"]
        mutations.append(missing)
        version = contract()
        version["packages"]["alpha"]["version"] = "2"
        mutations.append(version)
        root = contract()
        root["packages"]["alpha"]["wheel_sha256"] = "A" * 64
        mutations.append(root)
        hidden = contract()
        hidden["protocol"]["authority"] = True
        mutations.append(hidden)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                check_composition.validate_contract(value, packages())

    def test_fixture_imports_reject_private_external_and_incomplete_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.py"
            for source in (
                "import codex_app_server_client.compatibility\n",
                "import third_party\n",
                "import codex_app_server_client\n",
            ):
                with self.subTest(source=source):
                    path.write_text(source, encoding="utf-8")
                    with self.assertRaises(RuntimeError):
                        check_composition.validate_fixture_imports(path)

            exact_imports = (
                "import codex_app_server_client as client_api\n"
                "import embedded_service_contract as lifecycle_api\n"
                "import embedded_service_contract.testing as lifecycle_testing\n"
                "import runtime_manifest as manifest_api\n"
            )
            path.write_text(exact_imports + "client_api.compatibility\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "non-public package attribute"):
                check_composition.validate_fixture_imports(path)

    def test_artifact_bytes_and_content_root_are_independent_exact_inputs(self) -> None:
        expected = contract()["packages"]["alpha"]
        check_composition.verify_artifact(
            "alpha",
            wheel_sha256="a" * 64,
            content_root_sha256="b" * 64,
            expected=expected,
        )
        with self.assertRaisesRegex(RuntimeError, "wheel bytes differ"):
            check_composition.verify_artifact(
                "alpha",
                wheel_sha256="0" * 64,
                content_root_sha256="b" * 64,
                expected=expected,
            )
        with self.assertRaisesRegex(RuntimeError, "content root differs"):
            check_composition.verify_artifact(
                "alpha",
                wheel_sha256="a" * 64,
                content_root_sha256="0" * 64,
                expected=expected,
            )

    def test_result_rejects_hidden_fields_and_root_or_scenario_drift(self) -> None:
        full_contract = {
            "schema_version": 1,
            "packages": {
                name: {
                    "version": "0.1.0",
                    "wheel_sha256": character * 64,
                    "wheel_content_root_sha256": character * 64,
                }
                for name, character in zip(
                    sorted(
                        {
                            "codex-app-server-client",
                            "embedded-service-contract",
                            "runtime-manifest",
                        }
                    ),
                    "abc",
                    strict=True,
                )
            },
            "protocol": {
                "version": "0.147.0",
                "schema_root_sha256": "d" * 64,
                "selected_surface_root_sha256": "e" * 64,
            },
        }
        result = {
            "client": {
                "channel_close_count": 1,
                "generation": 1,
                "listed_threads": 0,
                "transport": "injected-byte-channel",
            },
            "incompatible_root_kinds": ["dependency-root", "protocol-schema"],
            "lifecycle": {
                "embedded": {"events": 6, "scenarios": 3, "shape": "embedded"},
                "process_owner_count": 1,
                "service": {"events": 6, "scenarios": 3, "shape": "service"},
            },
            "manifest_compatible": True,
            "manifest_sha256": "f" * 64,
            "packages": {
                name: record["version"] for name, record in full_contract["packages"].items()
            },
            "protocol": full_contract["protocol"],
            "public_modules": sorted(check_composition.PACKAGE_MODULES),
            "schema_version": 1,
        }
        check_composition.validate_result(result, full_contract)
        for mutation in ("hidden", "protocol", "owner"):
            changed = copy.deepcopy(result)
            if mutation == "hidden":
                changed["authority"] = "approved"
            elif mutation == "protocol":
                changed["protocol"]["schema_root_sha256"] = "0" * 64
            else:
                changed["lifecycle"]["process_owner_count"] = 2
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                check_composition.validate_result(changed, full_contract)


if __name__ == "__main__":
    unittest.main()
