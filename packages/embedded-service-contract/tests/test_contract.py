from __future__ import annotations

import inspect
import json
import re
import unittest
from dataclasses import FrozenInstanceError
from importlib.resources import files
from pathlib import Path

import embedded_service_contract as contract
from embedded_service_contract import (
    ConformanceError,
    HostContract,
    HostShape,
    LifecycleHost,
    RunRef,
    UnknownRunError,
    assert_lifecycle_conformance,
)
from embedded_service_contract.testing import (
    EmbeddedReferenceHost,
    ServiceReferenceHost,
    embedded_fixture,
    missing_operation_fixture,
    out_of_order_fixture,
    service_fixture,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def contract_json(name: str) -> dict[str, object]:
    resource = files("embedded_service_contract").joinpath("_contract", name)
    if resource.is_file():
        return json.loads(resource.read_text(encoding="utf-8"))
    return json.loads((PACKAGE_ROOT / "contract" / name).read_text(encoding="utf-8"))


class StructuralValueTests(unittest.TestCase):
    def test_host_shape_enforces_single_process_owner(self) -> None:
        self.assertEqual(HostContract(HostShape.EMBEDDED, 0).process_owner_count, 0)
        self.assertEqual(HostContract(HostShape.SERVICE, 1).process_owner_count, 1)
        for shape, owners in (
            (HostShape.EMBEDDED, 1),
            (HostShape.SERVICE, 0),
            (HostShape.SERVICE, 2),
        ):
            with self.subTest(shape=shape, owners=owners), self.assertRaises(ValueError):
                HostContract(shape, owners)

    def test_structural_values_are_frozen_and_bounded(self) -> None:
        ref = RunRef("run")
        with self.assertRaises(FrozenInstanceError):
            ref.value = "changed"  # type: ignore[misc]
        for invalid in ("", "x" * 257, "line\nbreak"):
            with self.subTest(invalid=invalid[:20]), self.assertRaises(ValueError):
                RunRef(invalid)

    def test_protocol_is_structural_and_has_exact_operations(self) -> None:
        self.assertIsInstance(EmbeddedReferenceHost(), LifecycleHost)
        self.assertIsInstance(ServiceReferenceHost(), LifecycleHost)
        operations = {
            name
            for name, value in inspect.getmembers(LifecycleHost)
            if callable(value) and not name.startswith("_")
        }
        self.assertEqual(operations, {"start", "status", "events", "cancel", "outcome"})


class ReferenceConformanceTests(unittest.TestCase):
    def test_two_distinct_reference_hosts_pass_one_contract(self) -> None:
        embedded = assert_lifecycle_conformance(embedded_fixture())
        service = assert_lifecycle_conformance(service_fixture())
        self.assertEqual((embedded.shape, service.shape), (HostShape.EMBEDDED, HostShape.SERVICE))
        self.assertEqual(embedded.scenarios, service.scenarios)
        self.assertEqual(embedded.observed_events, service.observed_events)
        self.assertIs(type(EmbeddedReferenceHost()).__base__, object)
        self.assertIs(type(ServiceReferenceHost()).__base__, object)

    def test_reference_hosts_do_not_share_state(self) -> None:
        embedded = EmbeddedReferenceHost()
        service = ServiceReferenceHost()
        ref = embedded.start(embedded_fixture().successful_request)
        with self.assertRaises(UnknownRunError):
            service.status(ref)
        with self.assertRaises(UnknownRunError):
            EmbeddedReferenceHost().status(ref)

    def test_failure_fixtures_are_deterministically_rejected(self) -> None:
        for fixture in (out_of_order_fixture(), missing_operation_fixture()):
            with self.subTest(factory=fixture.host_factory), self.assertRaises(ConformanceError):
                assert_lifecycle_conformance(fixture)


class FrozenPackageContractTests(unittest.TestCase):
    def test_structural_manifest_matches_public_api_and_exclusions(self) -> None:
        manifest = contract_json("structural-contract.json")
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(set(manifest["root_exports"]), set(contract.__all__))
        self.assertEqual(len(contract.__all__), 19)
        self.assertEqual(
            set(manifest["operations"]),
            {"start", "status", "events", "cancel", "outcome"},
        )
        exclusions = set(manifest["authority_exclusions"])
        self.assertIn("authorization", exclusions)
        self.assertIn("acceptance", exclusions)
        self.assertIn("product lifecycle", exclusions)

    def test_conformance_and_python_manifests_match_package(self) -> None:
        conformance = contract_json("conformance-fixtures.json")
        supported = contract_json("supported-python.json")
        self.assertEqual(conformance["schema_version"], 1)
        self.assertEqual(set(conformance["reference_hosts"]), {"embedded", "service"})
        self.assertEqual(set(conformance["scenarios"]), {"success", "failure", "cancellation"})
        self.assertIn("multiple-process-owners", conformance["failure_fixtures"])
        self.assertEqual(supported["requires_python"], ">=3.11")
        self.assertEqual(supported["acceptance_interpreters"], ["3.11", "3.14"])

    def test_readme_example_executes_through_public_imports(self) -> None:
        readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
        examples = re.findall(r"```python executable\n(.*?)```", readme, flags=re.DOTALL)
        self.assertEqual(len(examples), 1)
        exec(compile(examples[0], "README.md", "exec"), {"__name__": "__docs_example__"})

    def test_package_has_no_framework_or_downstream_dependency(self) -> None:
        pyproject = (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((PACKAGE_ROOT / "src").rglob("*.py"))
        ).lower()
        for prohibited in (
            "fastapi",
            "flask",
            "django",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, sources)


if __name__ == "__main__":
    unittest.main()
