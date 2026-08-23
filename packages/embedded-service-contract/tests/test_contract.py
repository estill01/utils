from __future__ import annotations

import inspect
import json
import re
import unittest
from dataclasses import FrozenInstanceError
from importlib.resources import files
from pathlib import Path

import embedded_service_contract as contract
import embedded_service_contract.testing as contract_testing
from embedded_service_contract import (
    Cancelled,
    CancelResult,
    ConformanceError,
    ConformanceFixture,
    Failed,
    HostContract,
    HostShape,
    LifecycleHost,
    RunRef,
    RunState,
    RunStatus,
    Succeeded,
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


class _InvalidOwnerContract:
    shape = HostShape.EMBEDDED
    process_owner_count = 1
    schema_version = 1


class _InvalidOwnerHost(EmbeddedReferenceHost):
    contract = _InvalidOwnerContract()  # type: ignore[assignment]


class _WrongStatusRefHost(EmbeddedReferenceHost):
    def status(self, ref: RunRef) -> RunStatus:
        status = super().status(ref)
        return RunStatus(RunRef("wrong-status-ref"), status.state, status.last_event_sequence)


class _WrongCancelRefHost(EmbeddedReferenceHost):
    def cancel(self, ref: RunRef) -> CancelResult:
        result = super().cancel(ref)
        return CancelResult(RunRef("wrong-cancel-ref"), result.state, result.changed)


class _WrongOutcomeRefHost(EmbeddedReferenceHost):
    def outcome(self, ref: RunRef):
        outcome = super().outcome(ref)
        wrong = RunRef("wrong-outcome-ref")
        if type(outcome) is Succeeded:
            return Succeeded(wrong, outcome.value)
        if type(outcome) is Failed:
            return Failed(wrong, outcome.error)
        if type(outcome) is Cancelled:
            return Cancelled(wrong)
        return None


class _StalePostCancelStatusHost(EmbeddedReferenceHost):
    def status(self, ref: RunRef) -> RunStatus:
        status = super().status(ref)
        if status.state is RunState.CANCELLED:
            return RunStatus(ref, RunState.RUNNING, status.last_event_sequence)
        return status


class _SingleSlotReferenceHost(EmbeddedReferenceHost):
    def start(self, request):
        self._next_id = 1
        self._runs.clear()
        return super().start(request)


class _SharedStateReferenceHost(EmbeddedReferenceHost):
    _shared_runs = {}

    def __init__(self) -> None:
        super().__init__()
        self._runs = self._shared_runs


def contract_json(name: str) -> dict[str, object]:
    resource = files("embedded_service_contract").joinpath("_contract", name)
    if resource.is_file():
        return json.loads(resource.read_text(encoding="utf-8"))
    return json.loads((PACKAGE_ROOT / "contract" / name).read_text(encoding="utf-8"))


def adversarial_fixture(host_factory):
    fixture = embedded_fixture()
    return ConformanceFixture(
        host_factory=host_factory,
        successful_request=fixture.successful_request,
        failing_request=fixture.failing_request,
        cancellable_request=fixture.cancellable_request,
    )


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
        with self.assertRaises(TypeError):
            HostContract(HostShape.EMBEDDED, 0, schema_version=True)
        with self.assertRaises(TypeError):
            HostContract("embedded", 0)  # type: ignore[arg-type]

    def test_structural_values_are_frozen_and_bounded(self) -> None:
        ref = RunRef("run")
        with self.assertRaises(FrozenInstanceError):
            ref.value = "changed"  # type: ignore[misc]
        for invalid in ("", "x" * 257, "line\nbreak"):
            with self.subTest(invalid=invalid[:20]), self.assertRaises(ValueError):
                RunRef(invalid)
        for invalid_ref in ("not-a-ref", 1, None):
            for outcome_type, field in (
                (Succeeded, "value"),
                (Failed, "error"),
            ):
                with (
                    self.subTest(outcome_type=outcome_type, invalid_ref=invalid_ref),
                    self.assertRaises(TypeError),
                ):
                    outcome_type(invalid_ref, **{field: "fixture"})  # type: ignore[arg-type]
            with self.subTest(invalid_ref=invalid_ref), self.assertRaises(TypeError):
                Cancelled(invalid_ref)  # type: ignore[arg-type]

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

    def test_same_shape_instances_keep_refs_unambiguous_after_both_start(self) -> None:
        for host_type, fixture_factory in (
            (EmbeddedReferenceHost, embedded_fixture),
            (ServiceReferenceHost, service_fixture),
        ):
            first = host_type()
            second = host_type()
            fixture = fixture_factory()
            first_ref = first.start(fixture.successful_request)
            second_ref = second.start(fixture.failing_request)
            with self.subTest(host_type=host_type):
                self.assertNotEqual(first_ref, second_ref)
                with self.assertRaises(UnknownRunError):
                    first.status(second_ref)
                with self.assertRaises(UnknownRunError):
                    second.status(first_ref)

    def test_failure_fixtures_are_deterministically_rejected(self) -> None:
        for fixture in (out_of_order_fixture(), missing_operation_fixture()):
            with self.subTest(factory=fixture.host_factory), self.assertRaises(ConformanceError):
                assert_lifecycle_conformance(fixture)

    def test_owner_ref_and_state_incoherence_are_rejected(self) -> None:
        for host_factory in (
            _InvalidOwnerHost,
            _WrongStatusRefHost,
            _WrongCancelRefHost,
            _WrongOutcomeRefHost,
            _StalePostCancelStatusHost,
            _SingleSlotReferenceHost,
            _SharedStateReferenceHost,
        ):
            with self.subTest(host_factory=host_factory), self.assertRaises(ConformanceError):
                assert_lifecycle_conformance(adversarial_fixture(host_factory))


class FrozenPackageContractTests(unittest.TestCase):
    def test_structural_manifest_matches_public_api_and_exclusions(self) -> None:
        manifest = contract_json("structural-contract.json")
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["package_version"], contract.__version__)
        self.assertEqual(manifest["root_exports"], contract.__all__)
        self.assertEqual(len(contract.__all__), 19)
        public_signature_names = (
            "HostContract",
            "RunRef",
            "RunStatus",
            "EventRecord",
            "CancelResult",
            "Succeeded",
            "Failed",
            "Cancelled",
            "ConformanceFixture",
            "ConformanceReport",
            "assert_lifecycle_conformance",
        )
        self.assertEqual(
            manifest["public_signatures"],
            {
                name: str(inspect.signature(getattr(contract, name)))
                for name in public_signature_names
            },
        )
        protocol_members = {
            "contract.getter": contract.LifecycleHost.contract.fget,
            **{
                name: getattr(contract.LifecycleHost, name)
                for name in ("start", "status", "events", "cancel", "outcome")
            },
        }
        self.assertEqual(
            manifest["protocol_signatures"],
            {name: str(inspect.signature(value)) for name, value in protocol_members.items()},
        )
        self.assertEqual(manifest["testing_exports"], contract_testing.__all__)
        self.assertEqual(
            manifest["testing_signatures"],
            {
                name: str(inspect.signature(getattr(contract_testing, name)))
                for name in manifest["testing_signatures"]
            },
        )
        self.assertEqual(
            manifest["enum_values"],
            {
                "HostShape": {value.name: value.value for value in HostShape},
                "RunState": {value.name: value.value for value in RunState},
                "ReferenceAction": {
                    value.name: value.value for value in contract_testing.ReferenceAction
                },
            },
        )
        self.assertEqual(
            manifest["error_hierarchy"],
            {
                name: getattr(contract, name).__bases__[0].__name__
                for name in (
                    "LifecycleContractError",
                    "UnknownRunError",
                    "InvalidCursorError",
                    "ConformanceError",
                )
            },
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
